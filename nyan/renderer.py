import copy
import os
import json
from urllib.parse import urlsplit
from collections import defaultdict, Counter
from datetime import datetime
from statistics import mean

from jinja2 import Environment, FileSystemLoader

from nyan.clusters import Cluster
from nyan.util import get_current_ts


class Renderer:
    def __init__(self, config_path, channels):
        assert os.path.exists(config_path)
        with open(config_path) as r:
            config = json.load(r)

        self.channels = channels

        file_loader = FileSystemLoader(".")
        env = Environment(loader=file_loader)
        self.cluster_template = env.get_template(config["cluster_template"])
        self.ratings_template = None
        if "ratings_template" in config:
            self.ratings_template = env.get_template(config["ratings_template"])

    def render_cluster(self, cluster: Cluster):
        groups = defaultdict(list)
        emojis = dict()
        for doc in cluster.docs:
            groups[doc.group].append(doc)
            emojis[doc.group] = self.channels[doc.channel_id].emoji

        used_channels = set()
        for group_name, group in groups.items():
            group.sort(key=lambda x: x.pub_time)
            filtered_group = list()
            for doc in group:
                if doc.channel_id in used_channels:
                    continue
                used_channels.add(doc.channel_id)
                filtered_group.append(doc)
            groups[group_name] = filtered_group

        groups = list(sorted(groups.items(), key=lambda x: x[0]))

        first_doc = copy.deepcopy(cluster.first_doc)
        first_doc.pub_time = datetime.fromtimestamp(first_doc.pub_time + 3 * 3600)

        external_link = None
        if cluster.external_links:
            external_link_url, el_cnt = cluster.external_links.most_common()[0]
            external_link_host = urlsplit(external_link_url).netloc
            if el_cnt >= 2:
                external_link = {
                    "url": external_link_url,
                    "host": external_link_host
                }

        views = self.views_to_str(cluster.views)
        return self.cluster_template.render(
            annotation_doc=cluster.annotation_doc,
            first_doc=first_doc,
            groups=groups,
            emojis=emojis,
            views=views,
            is_important=cluster.is_important,
            external_link=external_link
        )

    def render_discussion_message(self, doc):
        return '<a href="{}">{}</a>'.format(doc.url, doc.channel_title)

    def render_ratings(
        self,
        clusters,
        channels,
        duration
    ):
        if not self.ratings_template:
            return None
        cluster_count = 0
        lags = []
        channels_cnt, collocations, first_docs = Counter(), Counter(), Counter()
        best_blue_cluster, best_red_cluster, best_cluster = Cluster(), Cluster(), Cluster()

        for message_id, cluster in clusters.items():
            if cluster.pub_time_percentile < get_current_ts() - duration:
                continue

            cluster_count += 1
            if cluster.create_time:
                lags.append(abs(cluster.create_time - cluster.pub_time_percentile))

            cluster_group = cluster.group
            if cluster_group == "blue" and cluster.views > best_blue_cluster.views:
                best_blue_cluster = cluster
            elif cluster_group == "red" and cluster.views > best_red_cluster.views:
                best_red_cluster = cluster

            if cluster.views > best_cluster.views:
                best_cluster = cluster

            cluster_channels_ids = cluster.channels
            channels_cnt.update(cluster_channels_ids)
            first_docs[cluster.first_doc.channel_id.lower()] += 1
            for i, ch1 in enumerate(cluster_channels_ids):
                for j, ch2 in enumerate(cluster_channels_ids):
                    if i < j:
                        collocations[(ch1, ch2)] += 1

        assert best_cluster
        if not best_red_cluster.message_id:
            best_red_cluster = None
        if not best_blue_cluster.message_id:
            best_blue_cluster = None

        average_lag_minutes = int(mean(lags) // 60)
        cluster_frequency = duration // 60 // cluster_count

        channels_cnt = [(channels[ch], cnt) for ch, cnt in channels_cnt.most_common()[:10]]
        collocations = [
            ((channels[ch1], channels[ch2]), cnt)
            for (ch1, ch2), cnt in collocations.most_common()[:10]
        ]
        first_docs = [(channels[ch], cnt) for ch, cnt in first_docs.most_common()[:10]]

        return self.ratings_template.render(
            cluster_count=cluster_count,
            average_lag_minutes=average_lag_minutes,
            cluster_frequency=cluster_frequency,
            channels_cnt=channels_cnt,
            collocations=collocations,
            first_docs=first_docs,
            best_cluster=best_cluster,
            best_blue_cluster=best_blue_cluster,
            best_red_cluster=best_red_cluster
        )

    @staticmethod
    def views_to_str(views):
        if views >= 1000000:
            return "{:.1f}M".format(views / 1000000).replace(".", ",")
        elif views >= 1000:
            return "{:.1f}K".format(views / 1000).replace(".", ",")
        return views
