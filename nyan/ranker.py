import json
import logging
import os
from typing import List, Dict
from collections import defaultdict

from nyan.clusters import Cluster


class Ranker:
    def __init__(self, config_path: str) -> None:
        assert os.path.exists(config_path)
        with open(config_path) as r:
            self.config = json.load(r)

    def __call__(self, all_clusters: List[Cluster]) -> Dict[str, List[Cluster]]:
        issues = defaultdict(list)
        for cluster in all_clusters:
            for issue in cluster.issues:
                issues[issue].append(cluster)

        final_clusters = defaultdict(list)
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

            logging.info()
            logging.info(f"Issue: {issue_name}, clusters after first filter: {len(clusters)}")

            if len(clusters) <= 3:
                final_clusters[issue_name].extend(clusters)
                for cluster in clusters:
                    logging.info(
                        "Added as no other clusters: {} {}".format(
                            cluster.views_per_hour, cluster.cropped_title
                        )
                    )
                continue

            clusters = self.filter_by_views(
                clusters,
                issue_name,
                issue_config["views_percentile"],
                issue_config["higher_views_percentile"],
                issue_config["higher_trigger_age_minutes"],
            )
            clusters.sort(key=lambda c: c.pub_time_percentile)
            clusters = clusters[-10:]
            final_clusters[issue_name].extend(clusters)
        logging.info()
        return final_clusters

    def filter_by_views(
        self,
        clusters: List[Cluster],
        issue_name: str,
        views_percentile: int,
        higher_views_percentile: int,
        higher_trigger_age_minutes: int,
    ) -> List[Cluster]:
        all_views_per_hour = [cluster.views_per_hour for cluster in clusters]

        coefs = {"blue": 1.0, "red": 1.0, "purple": 1.0}
        if issue_name == "main":
            blue_views, red_views = 0, 0
            for cluster in clusters:
                group = cluster.group
                views = cluster.views_per_hour
                if group == "blue":
                    blue_views += views
                if group == "red":
                    red_views += views
            max_views = max(blue_views, red_views)
            coefs = {
                "blue": (max_views / blue_views) if blue_views != 0 else 1.0,
                "red": (max_views / red_views) if red_views != 0 else 1.0,
                "purple": 1.0,
            }
            logging.info("Blue views coefficient:", coefs["blue"])
            logging.info("Red views coefficient:", coefs["red"])

        all_views_per_hour = [
            int(v * coefs[c.group]) for v, c in zip(all_views_per_hour, clusters)
        ]
        all_views_per_hour.sort()
        n = len(all_views_per_hour)

        border_index = max(0, min(n - 1, n * views_percentile // 100))
        border_views_per_hour = all_views_per_hour[border_index]
        logging.info("Views border:", border_views_per_hour)

        higher_border_index = max(0, min(n - 1, n * higher_views_percentile // 100))
        higher_border_views_per_hour = all_views_per_hour[higher_border_index]
        logging.info("Higher views border:", higher_border_views_per_hour)

        hta = higher_trigger_age_minutes * 60
        filtered_clusters = []
        for cluster in clusters:
            views_per_hour = int(cluster.views_per_hour * coefs[cluster.group])
            cropped_title = cluster.cropped_title
            age = cluster.age
            if age > hta and views_per_hour >= border_views_per_hour:
                filtered_clusters.append(cluster)
                logging.info("Added by views: {} {}".format(views_per_hour, cropped_title))
            elif age < hta and views_per_hour >= higher_border_views_per_hour:
                cluster.is_important = True
                filtered_clusters.append(cluster)
                logging.info(
                    "Added by views (important): {} {}".format(
                        views_per_hour, cropped_title
                    )
                )
            elif not cluster.messages:
                logging.info("Skipped by views: {} {}".format(views_per_hour, cropped_title))
        return filtered_clusters
