import logging
from dataclasses import dataclass
from time import sleep
from typing import Optional, Sequence, List, Dict, Any, cast
from multiprocessing.pool import ThreadPool

import openai
import copy


MIN_MAX_TOKENS = 128


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
    model_name: str = "gpt-4",
    sleep_time: int = 2,
) -> str:
    decoding_args = copy.deepcopy(decoding_args)
    assert decoding_args.n == 1
    while True:
        try:
            completions = openai.ChatCompletion.create(  # type: ignore
                messages=messages, model=model_name, **decoding_args.__dict__
            )
            break
        except Exception as e:
            logging.warning("OpenAI error: %s.", e)
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
    return cast(str, completions.choices[0].message.content.strip())


def openai_batch_completion(
    batch: List[List[Dict[str, Any]]],
    decoding_args: OpenAIDecodingArguments = DEFAULT_ARGS,
    model_name: str = "gpt-4",
    sleep_time: int = 2,
) -> List[str]:
    if not batch:
        return []
    completions = []
    with ThreadPool(len(batch)) as pool:
        results = pool.starmap(
            openai_completion,
            [(messages, decoding_args, model_name, sleep_time) for messages in batch],
        )
        for result in results:
            completions.append(result)
    return completions
