from joblib import load

from nyan.embedder import Embedder


class ClassifierHead:
    def __init__(self, config):
        self.clf, self.label_encoder = load(config["path"])
        self.embedding_key = config["embedding_key"]
        self.not_news_threshold = config["not_news_threshold"]
        self.unknown_threshold = config["unknown_threshold"]

    def __call__(self, embedding, embedding_key):
        assert self.embedding_key == embedding_key
        scores = self.clf.predict_proba([embedding])[0]
        scores = {i: score for i, score in enumerate(scores)}
        scores = {
            self.label_encoder.inverse_transform([k])[0]: v
            for k, v in scores.items()
        }
        pairs = [(score, cat) for cat, score in scores.items()]
        best_score, best_category = max(pairs)

        category = best_category
        if scores.get("not_news", 0.0) >= self.not_news_threshold:
            category = "not_news"
        elif best_score < self.unknown_threshold:
            category = "unknown"
        return category, scores
