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


def main(
    input_path,
    documents_offset,
    posted_clusters_path,
    client_config_path,
    annotator_config_path,
    clusterer_config_path,
    ranker_config_path,
    channels_info_path,
    renderer_config_path,
    mongo_config_path
):
    assert input_path and not mongo_config_path or mongo_config_path and not input_path
    client = TelegramClient(client_config_path)
    annotator = Annotator(annotator_config_path, channels_info_path)
    channels = Channels(channels_info_path)
    clusterer = Clusterer(clusterer_config_path)
    renderer = Renderer(renderer_config_path, channels)
    ranker = Ranker(ranker_config_path)

    while True:
        if input_path and not os.path.exists(input_path):
            print("No input documents!")
            continue

        print("===== New iteration =====")
        posted_clusters = Clusters()
        if mongo_config_path:
            print("Reading clusters from Mongo")
            posted_clusters = Clusters.load_from_mongo(mongo_config_path)
        elif posted_clusters_path and os.path.exists(posted_clusters_path):
            print("Reading clusters from file")
            posted_clusters = Clusters.load(posted_clusters_path)
        print("{} clusters loaded".format(len(posted_clusters)))

        try:
            if input_path and os.path.exists(input_path):
                print("Reading docs from file")
                docs = read_documents_file(input_path, get_current_ts(), documents_offset)
            elif mongo_config_path:
                print("Reading docs from Mongo")
                docs = read_documents_mongo(mongo_config_path, get_current_ts(), documents_offset)
            else:
                assert False
            print("{} docs loaded".format(len(docs)))
            max_pub_time = ts_to_dt(max([d.pub_time for d in docs]))
            print("Last document: {}".format(max_pub_time))

        except Exception as e:
            print(e)
            print("Waiting for correct documents...")
            continue
        if not docs:
            print("Waiting for documents...")
            sleep(10)
            continue

        doc_channels_cnt = Counter()
        for doc in docs:
            doc_channels_cnt[doc.channel_id] += 1
        for channel_id, channel in channels:
            cnt = doc_channels_cnt.get(channel_id, 0)
            if cnt <= 1 and not channel.disabled and channel.issue == "main":
                print("Warning: {} docs from channel {}".format(cnt, channel_id))

        old_annotated_docs, remaining_docs = read_annotated_documents_mongo(mongo_config_path, docs)
        print("{} docs already annotated, {} docs to annotate".format(
            len(old_annotated_docs), len(remaining_docs))
        )

        annotated_docs = annotator(remaining_docs)
        print("{} docs after annotator".format(len(docs)))

        write_annotated_documents_mongo(mongo_config_path, annotated_docs)

        annotated_docs += old_annotated_docs
        print("{} docs before clustering".format(len(annotated_docs)))
        for doc in annotated_docs:
            assert doc.patched_text is not None

        updates_count = posted_clusters.update_documents(annotated_docs)
        print("{} updated documents".format(updates_count))

        new_clusters = clusterer(annotated_docs)
        print("{} clusters overall".format(len(new_clusters)))

        new_clusters = ranker(new_clusters)
        print("{} clusters in all issues after filtering".format(len(new_clusters)))

        for i, cluster in enumerate(new_clusters):
            posted_cluster = posted_clusters.find_similar(cluster)
            if posted_cluster:
                message = posted_cluster.message
                discussion_message = client.get_discussion(message)

                new_docs_pub_time = 0
                for doc in cluster.docs:
                    if not posted_cluster.has(doc):
                        posted_cluster.add(doc)
                        discussion_text = renderer.render_discussion_message(doc)
                        client.send_discussion_message(discussion_text, discussion_message)
                        new_docs_pub_time = max(doc.pub_time, new_docs_pub_time)
                        sleep(0.3)

                current_ts = get_current_ts()
                time_diff = abs(current_ts - posted_cluster.pub_time_percentile)
                if time_diff < 3600 * 3 and posted_cluster.changed():
                    cluster_text = renderer.render_cluster(posted_cluster)
                    print()
                    print("Update cluster {} at {}: {}".format(message.message_id, message.issue, posted_cluster.cropped_title))
                    print("Discussion message id: {}".format(discussion_message.message_id))

                    is_caption = bool(posted_cluster.images) or bool(posted_cluster.videos)
                    client.update_message(message, cluster_text, is_caption)
                else:
                    print()
                    print("Same cluster {} at {}: {}".format(message.message_id, message.issue, posted_cluster.cropped_title))
                continue

            cluster_text = renderer.render_cluster(cluster)
            print()
            print("New cluster in {}: {}".format(cluster.issue, cluster.cropped_title))

            issue_name = cluster.issue
            client.update_discussion_mapping(issue_name)
            message = client.send_message(cluster_text, issue_name, photos=cluster.images, videos=cluster.videos)
            if message is None:
                continue

            cluster.create_time = get_current_ts()
            cluster.message = message
            posted_clusters.add(cluster)

            print("Message id: {}, saving".format(message.message_id))
            if posted_clusters_path:
                posted_clusters.save(posted_clusters_path)
            if mongo_config_path:
                posted_clusters.save_to_mongo(mongo_config_path)

            client.update_discussion_mapping(issue_name)
            discussion_message = client.get_discussion(message)
            print("Discussion message id: {}".format(discussion_message.message_id))

            for doc in cluster.docs:
                discussion_text = renderer.render_discussion_message(doc)
                client.send_discussion_message(discussion_text, discussion_message)
                sleep(0.3)

        print()
        if posted_clusters_path:
            posted_clusters.save(posted_clusters_path)
            print("{} clusters saved to file".format(len(posted_clusters)))
        if mongo_config_path:
            saved_count = posted_clusters.save_to_mongo(mongo_config_path)
            print("{} clusters saved to Mongo".format(saved_count))
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", type=str, default=None)
    parser.add_argument("--documents-offset", type=int, default=12 * 3600)
    parser.add_argument("--channels-info-path", type=str, default="channels.json")
    parser.add_argument("--mongo-config-path", type=str, default=None)
    parser.add_argument("--posted-clusters-path", type=str, default=None)
    parser.add_argument("--client-config-path", type=str, default="configs/client_config.json")
    parser.add_argument("--annotator-config-path", type=str, default="configs/annotator_config.json")
    parser.add_argument("--clusterer-config-path", type=str, default="configs/clusterer_config.json")
    parser.add_argument("--renderer-config-path", type=str, default="configs/renderer_config.json")
    parser.add_argument("--ranker-config-path", type=str, default="configs/ranker_config.json")
    args = parser.parse_args()
    main(**vars(args))
