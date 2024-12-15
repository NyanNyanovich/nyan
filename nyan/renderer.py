import copy
import os
import json
from urllib.parse import urlsplit
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader

from nyan.clusters import Cluster
from nyan.channels import Channels
from nyan.document import Document
from nyan.util import ts_to_dt


class Renderer:
    def __init__(self, config_path: str, channels: Channels) -> None:
        assert os.path.exists(config_path)
        with open(config_path) as r:
            config = json.load(r)

        self.channels = channels

        file_loader = FileSystemLoader(".")
        env = Environment(loader=file_loader)
        self.cluster_template = env.get_template(config["cluster_template"])
        self.tz_offset = config["tz_offset"]
        self.tz_name = config["tz_name"]

    def render_cluster(self, cluster: Cluster, issue_name: str) -> str:
        groups = defaultdict(list)
        emojis = dict()
        colors = dict()
        for doc in cluster.docs:
            channel = self.channels[doc.channel_id]
            group = channel.groups[issue_name]
            groups[group].append(doc)
            if channel.emojis:
                emojis[group] = channel.emojis[issue_name]
            if channel.colors:
                colors[group] = channel.colors[issue_name]

        used_channels = set()
        for group_name, group_docs in groups.items():
            group_docs.sort(key=lambda x: x.pub_time)
            filtered_group = list()
            for doc in group_docs:
                if doc.channel_id in used_channels:
                    continue
                used_channels.add(doc.channel_id)
                filtered_group.append(doc)
            groups[group_name] = filtered_group

        sorted_groups = sorted(groups.items(), key=lambda x: x[0])
        first_doc = copy.deepcopy(cluster.first_doc)
        first_doc.pub_time_dt = ts_to_dt(first_doc.pub_time, self.tz_offset)

        external_link = None
        if cluster.external_links:
            external_link_url, el_cnt = cluster.external_links.most_common()[0]
            external_link_host = urlsplit(external_link_url).netloc
            if el_cnt >= 2:
                external_link = {"url": external_link_url, "host": external_link_host}

        views = self.views_to_str(cluster.views)
        return self.cluster_template.render(
            annotation_doc=cluster.annotation_doc,
            diff=cluster.diff,
            first_doc=first_doc,
            groups=sorted_groups,
            emojis=emojis,
            colors=colors,
            views=views,
            is_important=cluster.is_important,
            external_link=external_link,
            tz_name=self.tz_name,
        )

    def render_discussion_message(self, doc: Document) -> str:
        return '<a href="{}">{}</a>'.format(doc.url, doc.channel_title)

    @staticmethod
    def views_to_str(views: int) -> str:
        if views >= 1000000:
            return "{:.1f}M".format(views / 1000000).replace(".", ",")
        elif views >= 1000:
            return "{:.1f}K".format(views / 1000).replace(".", ",")
        return str(views)
