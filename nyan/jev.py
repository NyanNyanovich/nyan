import logging
from multiprocessing.pool import ThreadPool
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import httpx

from nyan.classifier import choose_category
from nyan.openai import get_provider


JEV_DEFAULT_MODEL = "typesafe/jev-1.13"
DECISIONS_PATH = "/api/alpha/decisions"


class JevClient:
    def __init__(
        self,
        model_name: str = JEV_DEFAULT_MODEL,
        api_url: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 3,
        sleep_time: float = 2.0,
    ) -> None:
        provider = get_provider(model_name, provider_name="openrouter")
        self.model_name = model_name
        if api_url is None:
            base = provider.api_base.rstrip("/")
            if base.endswith("/api/v1"):
                base = base[: -len("/api/v1")]
            api_url = base + DECISIONS_PATH
        self.api_url: str = api_url
        self.retries = retries
        self.sleep_time = sleep_time

        headers = dict(provider.headers)
        headers["Authorization"] = "Bearer {}".format(provider.api_key)
        self.client = httpx.Client(headers=headers, timeout=timeout)

    def decide(
        self, state: Dict[str, Any], questions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        payload = {"model": self.model_name, "state": state, "questions": questions}
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.client.post(self.api_url, json=payload)
                response.raise_for_status()
                answers = response.json()["answers"]
                assert isinstance(answers, dict)
                return answers
            except Exception as e:
                last_error = e
                logging.warning(
                    "Jev error (attempt %d/%d): %s", attempt, self.retries, e
                )
                if attempt < self.retries:
                    sleep(self.sleep_time * attempt)
        raise RuntimeError(
            "Jev request failed after {} attempts".format(self.retries)
        ) from last_error


class JevClassifierHead:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.client = JevClient(
            model_name=config.get("model_name", JEV_DEFAULT_MODEL),
            api_url=config.get("api_url"),
            timeout=config.get("timeout", 30.0),
            retries=config.get("retries", 3),
            sleep_time=config.get("sleep_time", 2.0),
        )
        self.instructions: str = config["instructions"]
        self.criteria: Dict[str, str] = config["criteria"]
        self.not_news_threshold: float = config["not_news_threshold"]
        self.unknown_threshold: float = config["unknown_threshold"]
        self.max_workers: int = config.get("max_workers", 8)
        self.max_text_length: int = config.get("max_text_length", 4000)

    def __call__(self, text: str) -> Tuple[str, Dict[str, float]]:
        state = {"text": text[: self.max_text_length]}
        questions = {
            "category": {
                "type": "choice",
                "instructions": self.instructions,
                "criteria": self.criteria,
            }
        }
        answer = self.client.decide(state, questions)["category"]
        probabilities = answer.get("probabilities", dict())
        scores = {cat: float(probabilities.get(cat, 0.0)) for cat in self.criteria}
        category = choose_category(
            scores, self.not_news_threshold, self.unknown_threshold
        )
        return category, scores

    def _safe_call(self, text: str) -> Optional[Tuple[str, Dict[str, float]]]:
        try:
            return self(text)
        except Exception as e:
            logging.warning("Jev classification failed, falling back: %s", e)
            return None

    def classify_many(
        self, texts: List[str]
    ) -> List[Optional[Tuple[str, Dict[str, float]]]]:
        if not texts:
            return []
        with ThreadPool(min(self.max_workers, len(texts))) as pool:
            return pool.map(self._safe_call, texts)
