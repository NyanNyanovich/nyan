import sys
import json

from scipy.spatial.distance import cosine
from sklearn.metrics import roc_auc_score, precision_recall_curve
import numpy as np

from nyan.labse import Embedder


def read_jsonl(path):
    with open(path) as r:
        return [json.loads(line) for line in r]


markup_path = sys.argv[1]
model_path = sys.argv[2]


markup = read_jsonl(markup_path)
embedder = Embedder(model_path)
y_pred, y_true = [], []
for record in markup:
    result = record["result"]
    #if record["agreement"] < 0.79:
    #    continue
    url1 = record["first_url"]
    url2 = record["second_url"]
    embeddings = embedder([record["first_text"], record["second_text"]])
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
