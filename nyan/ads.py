import json
import logging
import os
import traceback
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from jinja2 import Template

from nyan.openai import LLM
from nyan.text import fix_paragraphs


BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROMPT_PATH = str(BASE_DIR / "prompts/remove_ads.txt")


def normalize_spaces(text: str) -> str:
    return " ".join(text.split())


def compute_overlap(original: str, candidate: str) -> Tuple[float, float]:
    """
    Compares the candidate with the original char by char, ignoring whitespace.

    Returns (kept_ratio, new_ratio), where kept_ratio is the share of
    the original that survived in the candidate, and new_ratio is the share
    of the candidate that is not found in the original.
    A pure deletion has new_ratio == 0.0, a rewrite has new_ratio > 0.0.
    """
    original = normalize_spaces(original)
    candidate = normalize_spaces(candidate)
    if not original or not candidate:
        return 0.0, 1.0
    matcher = SequenceMatcher(None, original, candidate, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return matched / len(original), 1.0 - matched / len(candidate)


class AdRemover:
    """
    Removes ads from a text with an LLM, but only if the LLM actually
    removed something instead of rewriting the news. Every candidate is
    diffed against the original: anything that adds new text or strips
    too much of the original is discarded and the original is kept.
    """

    def __init__(self, config_path: str) -> None:
        assert os.path.exists(config_path)
        with open(config_path) as r:
            config: Dict[str, Any] = json.load(r)

        self.is_enabled: bool = config.get("is_enabled", True)
        self.max_new_ratio: float = config.get("max_new_ratio", 0.02)
        self.min_kept_ratio: float = config.get("min_kept_ratio", 0.6)
        self.min_kept_ratio_hard: float = config.get("min_kept_ratio_hard", 0.35)
        self.max_removed_length: int = config.get("max_removed_length", 250)
        self.min_length: int = config.get("min_length", 30)

        prompt_path: str = config.get("prompt_path", DEFAULT_PROMPT_PATH)
        assert os.path.exists(prompt_path)
        with open(prompt_path) as f:
            self.prompt_template = Template(f.read())

        self.llm = LLM(config=config["llm"])

    def __call__(self, text: str) -> str:
        if not self.is_enabled or not text:
            return text

        try:
            candidate = self.predict(text)
        except Exception:
            traceback.print_exc()
            return text

        clean_text = self.validate(text, candidate)
        if clean_text is None:
            return text
        return clean_text

    def predict(self, text: str) -> str:
        prompt = self.prompt_template.render(text=text).strip() + "\n"
        messages = [{"role": "user", "content": prompt}]
        content = self.llm(messages)
        content = content[content.find("{") : content.rfind("}") + 1]
        parsed_content: Dict[str, Any] = json.loads(content)
        return str(parsed_content["clean_text"])

    def validate(self, original: str, candidate: str) -> Optional[str]:
        candidate = fix_paragraphs(candidate.strip())
        if len(candidate) < self.min_length:
            logging.warning("Ad removal: candidate is too short, keeping original")
            return None

        kept_ratio, new_ratio = compute_overlap(original, candidate)
        if new_ratio > self.max_new_ratio:
            logging.warning(
                "Ad removal: text was rewritten (new_ratio %.3f), keeping original",
                new_ratio,
            )
            return None

        # A short post with a long boilerplate tail loses a big share of itself
        # legitimately, so a small absolute cut is allowed to go below
        # min_kept_ratio, but never below min_kept_ratio_hard.
        removed_length = round((1.0 - kept_ratio) * len(normalize_spaces(original)))
        is_small_cut = (
            removed_length <= self.max_removed_length
            and kept_ratio >= self.min_kept_ratio_hard
        )
        if kept_ratio < self.min_kept_ratio and not is_small_cut:
            logging.warning(
                "Ad removal: too much was stripped (kept_ratio %.3f, "
                "%d chars), keeping original",
                kept_ratio,
                removed_length,
            )
            return None
        return candidate
