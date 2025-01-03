import sys
import json

from scipy.spatial.distance import cosine
from sklearn.metrics import roc_auc_score, precision_recall_curve
import numpy as np

from nyan.embedder import Embedder


def read_jsonl(path):
    with open(path) as r:
        return [json.loads(line) for line in r]


markup_path = sys.argv[1]
model_path = sys.argv[2]


#embedder = Embedder(model_path, pooling_method="mean", normalize=True, text_prefix="query: ")
embedder = Embedder(model_path, pooling_method="cls", normalize=True)

markup = read_jsonl(markup_path)

y_true, texts = [], []
for record in markup:
    result = record["result"]
    texts.extend([record["first_text"], record["second_text"]])
    label = 1 - int(result == "ok")
    y_true.append(label)

embeddings = embedder(texts)

y_pred = []
for e1, e2 in zip(embeddings[::2], embeddings[1::2]):
    distance = cosine(e1, e2)
    y_pred.append(distance)

assert len(y_true) == len(y_pred)

print("AUC:", roc_auc_score(y_true, y_pred))
precision, recall, thresholds = precision_recall_curve(y_true, y_pred)
f1_scores = 2 * recall * precision / (recall + precision)
threshold = thresholds[np.argmax(f1_scores)]
f1 = max(f1_scores)
print('Best threshold: ', threshold)
print("F1: ", f1)
