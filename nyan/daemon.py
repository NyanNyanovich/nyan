import argparse
import os
from collections import Counter
from time import sleep
from datetime import datetime, timezone

from nyan.annotator import Annotator
from nyan.client import TelegramClient
from nyan.clusters import Clusters
from nyan.clusterer import Clusterer
from nyan.channels import Channels
from nyan.ranker import Ranker
from nyan.renderer import Renderer
from nyan.document import read_documents_file, read_documents_mongo
from nyan.document import read_annotated_documents_mongo, write_annotated_documents_mongo
from nyan.util import get_current_ts, ts_to_dt


class Daemon:
    def __init__(
        self,
        client_config_path,
        annotator_config_path,
        clusterer_config_path,
        ranker_config_path,
        channels_info_path,
        renderer_config_path
    ):
        self.client = TelegramClient(client_config_path)
        self.channels = Channels(channels_info_path)
        self.annotator = Annotator(annotator_config_path, self.channels)
        self.clusterer = Clusterer(clusterer_config_path)
        self.renderer = Renderer(renderer_config_path, self.channels)
        self.ranker = Ranker(ranker_config_path)

    def run(
        self,
        input_path,
        mongo_config_path,
        documents_offset,
        posted_clusters_path
    ):
        while True:
            self.__call__(
                input_path,
                mongo_config_path,
                documents_offset,
                posted_clusters_path
            )

    def __call__(
        self,
        input_path,
        mongo_config_path,
        documents_offset,
        posted_clusters_path
    ):
        assert input_path and not mongo_config_path or mongo_config_path and not input_path
        if input_path and not os.path.exists(input_path):
            print("No input documents!")
            return

        print("===== New iteration =====")
        posted_clusters = self.load_posted_clusters(mongo_config_path, posted_clusters_path)

        try:
            docs = self.read_documents(input_path, documents_offset, mongo_config_path)
        except Exception as e:
            print(e)
            print("Waiting for correct documents...")
            return
        if not docs:
            print("Waiting for documents...")
            sleep(10)
            return
        self.print_bad_channels(docs)
        annotated_docs = self.annotate_documents(docs, mongo_config_path)

        updates_count = posted_clusters.update_documents(annotated_docs)
        print("{} updated documents".format(updates_count))

        new_clusters = self.clusterer(annotated_docs)
        print("{} clusters overall".format(len(new_clusters)))

        new_clusters = self.ranker(new_clusters)
        print("{} clusters in all issues after filtering".format(len(new_clusters)))

        print()
        for cluster in new_clusters:
            self.send_cluster(cluster, posted_clusters, posted_clusters_path, mongo_config_path)

        print()
        if posted_clusters_path:
            posted_clusters.save(posted_clusters_path)
            print("{} clusters saved to file".format(len(posted_clusters)))
        if mongo_config_path:
            saved_count = posted_clusters.save_to_mongo(mongo_config_path)
            print("{} clusters saved to Mongo".format(saved_count))
            print()

    def load_posted_clusters(self, mongo_config_path, posted_clusters_path):
        posted_clusters = Clusters()
        if mongo_config_path:
            print("Reading clusters from Mongo")
            posted_clusters = Clusters.load_from_mongo(mongo_config_path)
        elif posted_clusters_path and os.path.exists(posted_clusters_path):
            print("Reading clusters from file")
            posted_clusters = Clusters.load(posted_clusters_path)
        print("{} clusters loaded".format(len(posted_clusters)))
        return posted_clusters

    def read_documents(self, input_path, documents_offset, mongo_config_path):
        if input_path and os.path.exists(input_path):
            print("Reading docs from file")
            docs = read_documents_file(input_path, get_current_ts(), documents_offset)
        elif mongo_config_path:
            print("Reading docs from Mongo")
            docs = read_documents_mongo(mongo_config_path, get_current_ts(), documents_offset)
        else:
            raise AssertionError()
        print("{} docs loaded".format(len(docs)))
        max_pub_time = ts_to_dt(max([d.pub_time for d in docs]))
        print("Last document: {}".format(max_pub_time))
        return docs

    def print_bad_channels(self, docs):
        doc_channels_cnt = Counter()
        for doc in docs:
            doc_channels_cnt[doc.channel_id] += 1
        for channel_id, channel in self.channels:
            cnt = doc_channels_cnt.get(channel_id, 0)
            if cnt <= 1 and not channel.disabled and channel.issue == "main":
                print("Warning: {} docs from channel {}".format(cnt, channel_id))

    def annotate_documents(self, docs, mongo_config_path):
        old_annotated_docs, remaining_docs = read_annotated_documents_mongo(mongo_config_path, docs)
        print("{} docs already annotated, {} docs to annotate".format(
            len(old_annotated_docs), len(remaining_docs))
        )

        annotated_docs = self.annotator(remaining_docs)
        print("{} docs after annotator".format(len(docs)))

        write_annotated_documents_mongo(mongo_config_path, annotated_docs)

        annotated_docs += old_annotated_docs
        for doc in annotated_docs:
            assert doc.patched_text is not None
        print("{} docs before clustering".format(len(annotated_docs)))
        return annotated_docs

    def send_cluster(self, cluster, posted_clusters, posted_clusters_path, mongo_config_path):
        posted_cluster = posted_clusters.find_similar(cluster)
        if posted_cluster:
            message = posted_cluster.message
            discussion_message = self.client.get_discussion(message)

            new_docs_pub_time = 0
            for doc in cluster.docs:
                if not posted_cluster.has(doc):
                    posted_cluster.add(doc)
                    discussion_text = self.renderer.render_discussion_message(doc)
                    self.client.send_discussion_message(discussion_text, discussion_message)
                    new_docs_pub_time = max(doc.pub_time, new_docs_pub_time)
                    sleep(0.3)

            current_ts = get_current_ts()
            time_diff = abs(current_ts - posted_cluster.pub_time_percentile)
            if time_diff < 3600 * 3 and posted_cluster.changed():
                cluster_text = self.renderer.render_cluster(posted_cluster)
                print("Update cluster {} at {}: {}".format(
                    message.message_id, message.issue, posted_cluster.cropped_title
                ))
                print("Discussion message id: {}".format(discussion_message.message_id))
                print()

                is_caption = bool(posted_cluster.images) or bool(posted_cluster.videos)
                self.client.update_message(message, cluster_text, is_caption)
            else:
                print("Same cluster {} at {}: {}".format(message.message_id, message.issue, posted_cluster.cropped_title))
            return

        cluster_text = self.renderer.render_cluster(cluster)
        print("New cluster in {}: {}".format(cluster.issue, cluster.cropped_title))

        issue_name = cluster.issue
        self.client.update_discussion_mapping(issue_name)
        message = self.client.send_message(cluster_text, issue_name, photos=cluster.images, videos=cluster.videos)
        if message is None:
            return

        cluster.create_time = get_current_ts()
        cluster.message = message
        posted_clusters.add(cluster)

        print("Message id: {}, saving".format(message.message_id))
        if posted_clusters_path:
            posted_clusters.save(posted_clusters_path)
        if mongo_config_path:
            posted_clusters.save_to_mongo(mongo_config_path)

        self.client.update_discussion_mapping(issue_name)
        discussion_message = self.client.get_discussion(message)
        print("Discussion message id: {}".format(discussion_message.message_id))

        for doc in cluster.docs:
            discussion_text = self.renderer.render_discussion_message(doc)
            self.client.send_discussion_message(discussion_text, discussion_message)
            sleep(0.3)
        print()
        return cluster
