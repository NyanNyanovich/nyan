from joblib import load

from nyan.embedder import Embedder


class ClassifierHead:
    def __init__(self, config):
        self.clf, self.label_encoder = load(config["path"])
        self.embedding_key = config["embedding_key"]

    def __call__(self, embedding, embedding_key):
        assert self.embedding_key == embedding_key
        scores = self.clf.predict_proba([embedding])[0]
        scores = {i: score for i, score in enumerate(scores)}
        return {
            self.label_encoder.inverse_transform([k])[0]: v
            for k, v in scores.items()
        }
