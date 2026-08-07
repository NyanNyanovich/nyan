import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Optional, Sequence, List, Dict, Any, cast
from multiprocessing.pool import ThreadPool

import openai
import copy
from dotenv import load_dotenv


MIN_MAX_TOKENS = 128
DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENAI_API_BASE = "https://api.openai.com/v1"


@dataclass
class Provider:
    name: str
    api_key: str
    api_base: str
    headers: Dict[str, str] = field(default_factory=dict)


def get_provider(model_name: str, provider_name: Optional[str] = None) -> Provider:
    load_dotenv(DOTENV_PATH)

    if provider_name is None:
        provider_name = os.environ.get("LLM_PROVIDER")
    if provider_name is None:
        provider_name = "openrouter" if "/" in model_name else "openai"
    provider_name = provider_name.lower()

    if provider_name == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set, put it in the environment or in .env"
            )
        headers = dict()
        site_url = os.environ.get("OPENROUTER_SITE_URL")
        app_name = os.environ.get("OPENROUTER_APP_NAME")
        if site_url:
            headers["HTTP-Referer"] = site_url
        if app_name:
            headers["X-Title"] = app_name
        return Provider(
            name=provider_name,
            api_key=api_key,
            api_base=os.environ.get("OPENROUTER_API_BASE", OPENROUTER_API_BASE),
            headers=headers,
        )

    if provider_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set, put it in the environment or in .env"
            )
        return Provider(
            name=provider_name,
            api_key=api_key,
            api_base=os.environ.get("OPENAI_API_BASE", OPENAI_API_BASE),
        )

    raise ValueError(f"Unknown provider: {provider_name}")


@dataclass
class OpenAIDecodingArguments:
    max_tokens: int = 2400
    temperature: float = 0.0
    top_p: float = 0.95
    n: int = 1
    stream: bool = False
    stop: Optional[Sequence[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0


DEFAULT_ARGS = OpenAIDecodingArguments()


def openai_completion(
    messages: List[Dict[str, Any]],
    decoding_args: OpenAIDecodingArguments = DEFAULT_ARGS,
    model_name: Optional[str] = None,
    sleep_time: int = 2,
    provider_name: Optional[str] = None,
) -> str:
    decoding_args = copy.deepcopy(decoding_args)
    assert decoding_args.n == 1
    assert model_name, "No model_name, pass it explicitly or use LLM"
    provider = get_provider(model_name, provider_name)
    while True:
        try:
            completions = openai.ChatCompletion.create(  # type: ignore
                messages=messages,
                model=model_name,
                api_key=provider.api_key,
                api_base=provider.api_base,
                headers=provider.headers,
                **decoding_args.__dict__,
            )
            break
        except Exception as e:
            logging.warning("%s error: %s.", provider.name, e)
            if "Please reduce" not in str(e):
                raise e
            new_max_tokens = int(decoding_args.max_tokens * 0.8)
            if new_max_tokens < MIN_MAX_TOKENS:
                logging.warning("Prompt is too long even at the minimum length.")
                raise e
            decoding_args.max_tokens = new_max_tokens
            logging.warning(
                "Reducing target length to %d, Retrying...",
                decoding_args.max_tokens,
            )
            sleep(sleep_time)
    choice = completions.choices[0]
    content = choice.message.get("content")
    if not content:
        raise RuntimeError(
            "Empty content from {}, finish_reason: {}. "
            "Reasoning models spend max_tokens ({}) on reasoning first, "
            "raise decoding_args.max_tokens in the LLM config.".format(
                model_name, choice.get("finish_reason"), decoding_args.max_tokens
            )
        )
    return cast(str, content.strip())


def openai_batch_completion(
    batch: List[List[Dict[str, Any]]],
    decoding_args: OpenAIDecodingArguments = DEFAULT_ARGS,
    model_name: Optional[str] = None,
    sleep_time: int = 2,
    provider_name: Optional[str] = None,
) -> List[str]:
    if not batch:
        return []
    completions = []
    with ThreadPool(len(batch)) as pool:
        results = pool.starmap(
            openai_completion,
            [
                (messages, decoding_args, model_name, sleep_time, provider_name)
                for messages in batch
            ],
        )
        for result in results:
            completions.append(result)
    return completions


class LLM:
    def __init__(self, config_path: str) -> None:
        assert os.path.exists(config_path)
        with open(config_path) as r:
            self.config: Dict[str, Any] = json.load(r)

        self.model_name: str = self.config["model_name"]
        self.provider_name: Optional[str] = self.config.get("provider_name")
        self.decoding_args = OpenAIDecodingArguments(
            **self.config.get("decoding_args", dict())
        )

    def __call__(self, messages: List[Dict[str, Any]]) -> str:
        return openai_completion(
            messages=messages,
            decoding_args=self.decoding_args,
            model_name=self.model_name,
            provider_name=self.provider_name,
        )
