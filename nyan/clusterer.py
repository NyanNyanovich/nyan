import json
import os

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
        distances_config = self.config["distances"]
        same_channels_penalty = distances_config.get("same_channels_penalty", 1.0)
        fix_same_channels = same_channels_penalty > 1.0
        time_penalty_modifier = distances_config.get("time_penalty_modifier", 1.0)
        fix_time = time_penalty_modifier > 1.0
        time_shift_hours = distances_config.get("time_shift_hours", 4)

        max_distance = 1.0
        embeddings = [d.embedding for d in docs]
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
                if fix_time:
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
        print("{} clusters".format(len(clusters)))

        clusters = self.filter_clusters(clusters)
        clusters.sort(key=lambda c: c.pub_time_percentile)
        return clusters

    def filter_clusters(self, clusters):
        filtering_config = self.config["filtering"]

        filtered_clusters = []
        for cluster in clusters:
            unique_channels = {d.channel_id for d in cluster.docs}
            is_big_cluster = len(unique_channels) >= filtering_config["min_channels"]
            has_ru_doc = any(doc.language == "ru" for doc in cluster.docs)
            is_fresh = cluster.age < filtering_config["max_age_minutes"] * 60
            if is_big_cluster and has_ru_doc and is_fresh:
                filtered_clusters.append(cluster)
        clusters = filtered_clusters

        if len(clusters) <= 3:
            return clusters

        all_views_per_hour = [cluster.views_per_hour for cluster in clusters]
        all_views_per_hour.sort()
        n = len(all_views_per_hour)

        views_percentile = filtering_config["views_percentile"]
        border_index = max(0, min(n - 1, n * views_percentile // 100))
        border_views_per_hour = all_views_per_hour[border_index]
        print("Views border:", border_views_per_hour)

        higher_views_percentile = filtering_config["higher_views_percentile"]
        higher_border_index = max(0, min(n - 1, n * higher_views_percentile // 100))
        higher_border_views_per_hour = all_views_per_hour[higher_border_index]
        print("Higher views border:", higher_border_views_per_hour)

        hta = filtering_config["higher_trigger_age_minutes"] * 60
        filtered_clusters = []
        for cluster in clusters:
            if cluster.age > hta and cluster.views_per_hour >= border_views_per_hour:
                filtered_clusters.append(cluster)
            elif cluster.age < hta and cluster.views_per_hour >= higher_border_views_per_hour:
                cluster.is_important = True
                filtered_clusters.append(cluster)
            elif cluster.message is None:
                print("Skipped by views: {} {}".format(cluster.views_per_hour, cluster.cropped_title))
        return filtered_clusters
