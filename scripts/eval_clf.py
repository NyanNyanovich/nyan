import fire
from joblib import load
from sklearn.metrics import classification_report, confusion_matrix

from nyan.embedder import Embedder
from nyan.util import read_jsonl


def eval_clf(
    markup_path,
    model_path,
    clf_path
):
    markup = list(read_jsonl(markup_path))
    embedder = Embedder(model_path, pooling_method="mean", text_prefix="query: ")
    embeddings = embedder([r["text"] for r in markup])
    clf, label_encoder = load(clf_path)

    y_pred, y_true = [], []
    for record, embedding in zip(markup, embeddings):
        text = record["text"]
        embedding = embedding.numpy()
        pred = clf.predict([embedding])
        predicted_cat = label_encoder.inverse_transform(pred)[0]
        labels = record["labels"]
        if predicted_cat not in labels:
            print()
            print(text)
            print("PRED:", predicted_cat)
            print("TRUE:", labels)
            y_true.append(labels[0])
        else:
            y_true.append(predicted_cat)
        y_pred.append(predicted_cat)

    print(classification_report(y_true, y_pred, target_names=label_encoder.classes_))
    print(confusion_matrix(y_true, y_pred))


if __name__ == "__main__":
    fire.Fire(eval_clf)
