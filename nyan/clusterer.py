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
        image_bonus = distances_config.get("image_bonus", 0.0)
        fix_images = image_bonus > 0.0
        if fix_images:
            image_idx2cluster = self.find_image_duplicates(docs)

        min_distance = 0.0
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
                is_time_fixable_issues = doc1.issue not in ntp_issues or doc2.issue not in ntp_issues
                if fix_same_channels and doc1.channel_id == doc2.channel_id:
                    distances[i1, i2] = min(max_distance, distances[i1, i2] * same_channels_penalty)
                    continue
                max_images_count = max(len(doc1.embedded_images), len(doc2.embedded_images))
                min_images_count = min(len(doc1.embedded_images), len(doc2.embedded_images))
                is_same_image_cluster = image_idx2cluster.get(i1, -1) == image_idx2cluster.get(i2, -2)
                if fix_images and min_images_count >= 1 and max_images_count <= 2 and is_same_image_cluster:
                    distances[i1, i2] = max(min_distance, distances[i1, i2] * (1.0 - image_bonus))
                if fix_time and is_time_fixable_issues:
                    time_diff = abs(doc1.pub_time - doc2.pub_time)
                    hours_shifted = (time_diff / 3600) - time_shift_hours
                    time_penalty = 1.0 + expit(hours_shifted) * (time_penalty_modifier - 1.0)
                    distances[i1, i2] = min(max_distance, distances[i1, i2] * time_penalty)

        clustering = AgglomerativeClustering(
            **self.config["clustering"]
        )

        labels = clustering.fit_predict(distances).tolist()
        clusters = [Cluster() for _ in range(max(labels) + 1)]
        for doc, l in zip(docs, labels):
            clusters[l].add(doc)
        return clusters

    def find_image_duplicates(self, docs):
        embeddings, image2doc = [], []
        for i, doc in enumerate(docs):
            for image in doc.embedded_images:
                embeddings.append(image["embedding"])
                image2doc.append(i)
        if not image2doc:
            return dict()

        dim = len(embeddings[0])
        np_embeddings = np.zeros((len(image2doc), dim), dtype=np.float32)
        for i, embedding in enumerate(embeddings):
            np_embeddings[i, :] = embedding
        embeddings = np_embeddings

        clustering = AgglomerativeClustering(
            n_clusters=None,
            affinity="cosine",
            linkage="average",
            distance_threshold=0.02
        )

        labels = clustering.fit_predict(embeddings).tolist()
        return {image2doc[i]: l for i, l in enumerate(labels)}
