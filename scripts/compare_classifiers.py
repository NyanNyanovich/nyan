import json
from typing import Dict, List, Optional, Sequence

import fire
from sklearn.metrics import classification_report

from nyan.classifier import ClassifierHead, choose_category
from nyan.embedder import Embedder
from nyan.jev import JevClassifierHead
from nyan.util import read_jsonl

TOPICAL = ("tech", "economy", "entertainment")


def summarize(records: Sequence[Dict], preds: List[str]) -> Dict[str, float]:
    n = len(records)
    labels = [set(r["labels"]) for r in records]
    correct = sum(p in ls for p, ls in zip(preds, labels))
    defined = [(p, ls) for p, ls in zip(preds, labels) if p != "unknown"]
    tp = sum(p == "not_news" and "not_news" in ls for p, ls in zip(preds, labels))
    fp = sum(p == "not_news" and "not_news" not in ls for p, ls in zip(preds, labels))
    fn = sum(p != "not_news" and "not_news" in ls for p, ls in zip(preds, labels))
    topical = [(p, ls) for p, ls in zip(preds, labels) if p in TOPICAL]
    return {
        "accuracy": correct / n,
        "unknown_share": (n - len(defined)) / n,
        "accuracy_defined": sum(p in ls for p, ls in defined) / max(1, len(defined)),
        "not_news_precision": tp / max(1, tp + fp),
        "not_news_recall": tp / max(1, tp + fn),
        "topical_precision": sum(p in ls for p, ls in topical) / max(1, len(topical)),
        "topical_count": len(topical),
    }


def report(records: Sequence[Dict], preds: List[str]) -> Dict:
    y_true = [p if p in r["labels"] else r["labels"][0] for r, p in zip(records, preds)]
    return classification_report(y_true, preds, output_dict=True, zero_division=0)


def compare(
    markup_path: str,
    config_path: str = "configs/annotator_config.json",
    jev_not_news_threshold: Optional[float] = None,
    jev_unknown_threshold: Optional[float] = None,
) -> None:
    with open(config_path) as r:
        config = json.load(r)
    records = list(read_jsonl(markup_path))
    texts = [r["text"] for r in records]

    embedder = Embedder(**config["embedder"])
    local_head = ClassifierHead(config["cat_detector"])
    embeddings = embedder(texts)
    local_scores = [
        local_head(e.numpy().tolist(), local_head.embedding_key)[1] for e in embeddings
    ]

    jev_config = config["jev_cat_detector"]
    if jev_not_news_threshold is not None:
        jev_config["not_news_threshold"] = jev_not_news_threshold
    if jev_unknown_threshold is not None:
        jev_config["unknown_threshold"] = jev_unknown_threshold
    jev_head = JevClassifierHead(jev_config)
    jev_results = jev_head.classify_many(texts)
    keep = [i for i, res in enumerate(jev_results) if res is not None]
    if len(keep) < len(records):
        print("Jev failed on {} records, they are skipped".format(len(records) - len(keep)))
    records = [records[i] for i in keep]
    local_scores = [local_scores[i] for i in keep]
    jev_scores = [jev_results[i][1] for i in keep]  # type: ignore

    def argmax(scores: Dict[str, float]) -> str:
        return max(scores, key=lambda k: scores[k])

    variants = {
        "local argmax": [argmax(s) for s in local_scores],
        "local thresholds {}/{}".format(
            local_head.not_news_threshold, local_head.unknown_threshold
        ): [
            choose_category(s, local_head.not_news_threshold, local_head.unknown_threshold)
            for s in local_scores
        ],
        "jev argmax": [argmax(s) for s in jev_scores],
        "jev thresholds {}/{}".format(
            jev_head.not_news_threshold, jev_head.unknown_threshold
        ): [
            choose_category(s, jev_head.not_news_threshold, jev_head.unknown_threshold)
            for s in jev_scores
        ],
    }
    print("\n{} records".format(len(records)))
    for name, preds in variants.items():
        metrics = summarize(records, preds)
        print("{:30s} ".format(name) + "  ".join(
            "{}={:.3f}".format(k, v) if isinstance(v, float) else "{}={}".format(k, v)
            for k, v in metrics.items()
        ))

    print("\nPer-class precision/recall/F1 (argmax):")
    reports = {
        "local": report(records, variants["local argmax"]),
        "jev": report(records, variants["jev argmax"]),
    }
    skip = ("accuracy", "macro avg", "weighted avg")
    classes = sorted(c for c in reports["local"] if c not in skip)
    print("{:14s} {:>5s}  {:>16s}  {:>16s}".format("class", "n", "local", "jev"))
    for c in classes:
        a = reports["local"].get(c, {})
        b = reports["jev"].get(c, {})
        print("{:14s} {:5d}  {:.2f}/{:.2f}/{:.2f}    {:.2f}/{:.2f}/{:.2f}".format(
            c, int(a.get("support", 0)),
            a.get("precision", 0), a.get("recall", 0), a.get("f1-score", 0),
            b.get("precision", 0), b.get("recall", 0), b.get("f1-score", 0),
        ))
    for name, rep in reports.items():
        print("{} macro F1 {:.3f}, accuracy {:.3f}".format(
            name, rep["macro avg"]["f1-score"], rep["accuracy"]
        ))


if __name__ == "__main__":
    fire.Fire(compare)
