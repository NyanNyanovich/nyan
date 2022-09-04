import json
import os

import numpy as np
from scipy.special import expit
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import pairwise_distances

from nyan.clusters import Cluster


class Clusterer:
    def __init__(self, config_path: str):
        assert os.path.exists(config_path)
        with open(config_path) as r:
            self.config = json.load(r)

    def __call__(self, docs):
        assert docs, "No docs for clusterer"

        distances_config = self.config["distances"]
        same_channels_penalty = distances_config.get("same_channels_penalty", 1.0)
        fix_same_channels = same_channels_penalty > 1.0
        time_penalty_modifier = distances_config.get("time_penalty_modifier", 1.0)
        fix_time = time_penalty_modifier > 1.0
        time_shift_hours = distances_config.get("time_shift_hours", 4)
        ntp_issues = distances_config.get("no_time_penalty_issues", tuple())

        max_distance = 1.0
        dim = len(docs[0].embedding)
        embeddings = np.zeros((len(docs), dim), dtype=np.float32)
        for i, doc in enumerate(docs):
            embeddings[i, :] = doc.embedding
        distances = pairwise_distances(
            embeddings,
            metric="cosine",
            force_all_finite=False
        )
        for i1, doc1 in enumerate(docs):
            for i2, doc2 in enumerate(docs):
                if i1 == i2:
                    continue
                if fix_same_channels and doc1.channel_id == doc2.channel_id:
                    distances[i1, i2] = min(max_distance, distances[i1, i2] * same_channels_penalty)
                    continue
                is_good_issue = doc1.issue not in ntp_issues or doc2.issue not in ntp_issues
                if fix_time and is_good_issue:
                    time_diff = abs(doc1.pub_time - doc2.pub_time)
                    hours_shifted = (time_diff / 3600) - time_shift_hours
                    time_penalty = 1.0 + expit(hours_shifted) * (time_penalty_modifier - 1.0)
                    distances[i1, i2] = min(max_distance, distances[i1, i2] * time_penalty)
                    continue

        clustering = AgglomerativeClustering(
            **self.config["clustering"]
        )

        labels = clustering.fit_predict(distances).tolist()
        clusters = [Cluster() for _ in range(max(labels) + 1)]
        for doc, l in zip(docs, labels):
            clusters[l].add(doc)
        return clusters
