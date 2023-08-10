from fasttext import load_model as ft_load_model
from pyonmttok import Tokenizer


class FasttextClassifier:
    def __init__(self, model_path, lower=False, use_tokenizer=False, max_tokens=50):
        self.model = ft_load_model(model_path)
        self.lower = lower
        self.use_tokenizer = use_tokenizer
        self.tokenizer = Tokenizer("conservative", joiner_annotate=False)
        self.max_tokens = max_tokens
        self.label_offset = len("__label__")

    def __call__(self, text):
        text = text.replace("\xa0", " ").strip()
        text = " ".join(text.split())

        if self.lower:
            text = text.lower()

        if self.use_tokenizer:
            tokens, _ = self.tokenizer.tokenize(text)
        else:
            tokens = text.split()

        text_sample = " ".join(tokens[:self.max_tokens])
        (label,), (prob,) = self.model.predict(text_sample, k=1)
        label = label[self.label_offset:]
        return label, prob
