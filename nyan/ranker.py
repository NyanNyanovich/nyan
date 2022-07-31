import json
import os
from typing import List
from collections import defaultdict

from nyan.clusters import Cluster


class Ranker:
    def __init__(self, config_path: str):
        assert os.path.exists(config_path)
        with open(config_path) as r:
            self.config = json.load(r)

    def __call__(self, all_clusters: List[Cluster]):
        issues = defaultdict(list)
        for cluster in all_clusters:
            issues[cluster.issue].append(cluster)

        final_clusters = []
        for issue_config in self.config["issues"]:
            issue_name = issue_config["issue_name"]
            min_channels = issue_config["min_channels"]
            max_age_minutes = issue_config["max_age_minutes"]

            clusters = issues[issue_name]
            filtered_clusters = []
            for cluster in clusters:
                unique_channels = {d.channel_id for d in cluster.docs}
                is_big_cluster = len(unique_channels) >= min_channels
                has_ru_doc = any(doc.language == "ru" for doc in cluster.docs)
                is_fresh = cluster.age < max_age_minutes * 60
                if is_big_cluster and has_ru_doc and is_fresh:
                    filtered_clusters.append(cluster)
            clusters = filtered_clusters

            if len(clusters) <= 3:
                final_clusters.extend(clusters)
                continue

            clusters = self.filter_by_views(
                clusters,
                issue_config["views_percentile"],
                issue_config["higher_views_percentile"],
                issue_config["higher_trigger_age_minutes"]
            )
            clusters.sort(key=lambda c: c.pub_time_percentile)
            clusters = clusters[-10:]
            final_clusters.extend(clusters)
        return final_clusters

    def filter_by_views(
        self,
        clusters,
        views_percentile: int,
        higher_views_percentile: int,
        higher_trigger_age_minutes: int
    ):
        all_views_per_hour = [cluster.views_per_hour for cluster in clusters]
        all_views_per_hour.sort()
        n = len(all_views_per_hour)

        border_index = max(0, min(n - 1, n * views_percentile // 100))
        border_views_per_hour = all_views_per_hour[border_index]
        print("Views border:", border_views_per_hour)

        higher_border_index = max(0, min(n - 1, n * higher_views_percentile // 100))
        higher_border_views_per_hour = all_views_per_hour[higher_border_index]
        print("Higher views border:", higher_border_views_per_hour)

        hta = higher_trigger_age_minutes * 60
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
