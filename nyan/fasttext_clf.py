from typing import Tuple

from fasttext import load_model as ft_load_model  # type: ignore
from pyonmttok import Tokenizer  # type: ignore


class FasttextClassifier:
    def __init__(
        self,
        model_path: str,
        lower: bool = False,
        use_tokenizer: bool = False,
        max_tokens: int = 50,
    ):
        self.model = ft_load_model(model_path)
        self.lower = lower
        self.use_tokenizer = use_tokenizer
        self.tokenizer = Tokenizer("conservative", joiner_annotate=False)
        self.max_tokens = max_tokens
        self.label_offset = len("__label__")

    def __call__(self, text: str) -> Tuple[str, float]:
        text = text.replace("\xa0", " ").strip()
        text = " ".join(text.split())

        if self.lower:
            text = text.lower()

        if self.use_tokenizer:
            tokens, _ = self.tokenizer.tokenize(text)
        else:
            tokens = text.split()

        text_sample = " ".join(tokens[: self.max_tokens])
        (label,), (prob,) = self.model.predict(text_sample, k=1)
        label = label[self.label_offset :]
        return label, prob
