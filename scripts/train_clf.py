import os
import fire
import json
from collections import defaultdict
from joblib import dump

import torch
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder

from nyan.util import read_jsonl, write_jsonl
from nyan.embedder import Embedder

CATEGORIES = '["not_news", "war", "economy", "tech", "science", "sports", "entertainment", "incident", "politics", "other"]'


def train(
    markup_path: str,
    model_path: str,
    output_path: str,
    embeddings_path: str,
    categories: str = CATEGORIES
):
    markup = list(read_jsonl(markup_path))
    categories = json.loads(categories)

    if os.path.exists(embeddings_path):
        embeddings = torch.load(embeddings_path)
    else:
        embedder = Embedder(model_path, pooling_method="mean", text_prefix="query: ")
        texts = [r["text"] for r in markup]
        embeddings = embedder(texts)
        torch.save(embeddings, embeddings_path)
    assert len(embeddings) == len(markup)

    X = embeddings.numpy()
    label_encoder = LabelEncoder()
    labels = [min([categories.index(l) for l in r["labels"]]) for r in markup]
    labels = [categories[l] for l in labels]
    y = label_encoder.fit_transform(labels)

    clf = MLPClassifier(
        hidden_layer_sizes=(256, 64),
        verbose=True,
        validation_fraction=0.1,
        learning_rate_init=0.0005,
        early_stopping=True,
        n_iter_no_change=100,
        max_iter=300
    )
    clf.fit(X, y)
    dump([clf, label_encoder], output_path)


if __name__ == "__main__":
    fire.Fire(train)
