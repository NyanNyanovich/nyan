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
docs_path = sys.argv[2]
model_path = sys.argv[3]


markup = read_jsonl(markup_path)
docs = read_jsonl(docs_path)
docs = {doc["url"]: doc for doc in docs}

embedder = Embedder(model_path)
y_pred = []
y_true = []
for record in markup:
    result = record["result"]
    if result == "trash":
        continue
    url1 = record["url1"]
    url2 = record["url2"]
    doc1 = docs[url1]
    doc2 = docs[url2]
    embeddings = embedder([doc1["text"], doc2["text"]])
    distance = cosine(embeddings[0], embeddings[1])
    y_pred.append(distance)
    label = 1 - int(result == "ok")
    y_true.append(label)

print("AUC:", roc_auc_score(y_true, y_pred))
precision, recall, thresholds = precision_recall_curve(y_true, y_pred)
f1_scores = 2 * recall * precision / (recall + precision)
threshold = thresholds[np.argmax(f1_scores)]
f1 = max(f1_scores)
print('Best threshold: ', threshold)
print("F1: ", f1)
