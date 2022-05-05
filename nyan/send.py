import argparse
import os
from collections import Counter
from time import sleep
from datetime import datetime, timezone

from nyan.annotator import Annotator
from nyan.client import TelegramClient
from nyan.clusters import Clusters
from nyan.clusterer import Clusterer
from nyan.document import read_documents_file, read_documents_mongo
from nyan.renderer import Renderer
from nyan.util import get_current_ts, ts_to_dt


def main(
    input_path,
    documents_offset,
    posted_clusters_path,
    client_config_path,
    annotator_config_path,
    clusterer_config_path,
    channels_info_path,
    renderer_config_path,
    mongo_config_path
):
    assert input_path and not mongo_config_path or mongo_config_path and not input_path
    client = TelegramClient(client_config_path)
    annotator = Annotator(annotator_config_path, channels_info_path)
    clusterer = Clusterer(clusterer_config_path)
    renderer = Renderer(renderer_config_path)

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
        else:
            assert False
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

        docs = annotator(docs)
        print("{} docs after annotator".format(len(docs)))

        updates_count = posted_clusters.update_documents(docs)
        print("{} updated documents".format(updates_count))

        new_clusters = clusterer(docs)
        print("{} clusters after filtering".format(len(new_clusters)))

        new_clusters = new_clusters[-10:]
        urls2messages = posted_clusters.urls2messages
        for i, cluster in enumerate(new_clusters):
            message_ids = [urls2messages.get(url) for url in cluster.urls if url in urls2messages]
            if message_ids:
                message_id = Counter(message_ids).most_common()[0][0]
                posted_cluster = posted_clusters[message_id]
                discussion_message_id = client.get_discussion(message_id)

                new_docs_pub_time = 0
                for doc in cluster.docs:
                    if not posted_cluster.has(doc):
                        posted_cluster.add(doc)
                        discussion_text = renderer.render_discussion_message(doc)
                        client.send_discussion_message(discussion_text, discussion_message_id)
                        new_docs_pub_time = max(doc.pub_time, new_docs_pub_time)
                        sleep(0.3)
                current_ts = get_current_ts()
                time_diff = abs(current_ts - posted_cluster.pub_time_percentile)
                if time_diff < 3600 * 3 and posted_cluster.changed():
                    cluster_text = renderer.render_cluster(posted_cluster)
                    print()
                    print("Update cluster {}: {}".format(message_id, posted_cluster.cropped_title))
                    print("Discussion message id: {}".format(discussion_message_id))

                    is_caption = bool(posted_cluster.images) or bool(posted_cluster.videos)
                    response = client.update_message(message_id, cluster_text, is_caption)
                    print("Update status code:", response.status_code)
                    if response.status_code != 200:
                        print("Update error:", response.text)
                else:
                    print()
                    print("Same cluster {}: {}".format(message_id, posted_cluster.cropped_title))
                continue

            cluster_text = renderer.render_cluster(cluster)
            print()
            print("New cluster:", cluster.cropped_title)

            client.update_discussion_mapping()
            response = client.send_message(cluster_text, photos=cluster.images, videos=cluster.videos)
            print("Send status code:", response.status_code)
            if response.status_code != 200:
                print("Send error:", response.text)
                continue

            result = response.json()["result"]
            message_id = int(result["message_id"] if "message_id" in result else result[0]["message_id"])
            cluster.message_id = message_id
            posted_clusters[message_id] = cluster
            print("Message id: {}".format(message_id))

            cluster.create_time = get_current_ts()

            client.update_discussion_mapping()
            discussion_message_id = client.get_discussion(message_id)
            print("Discussion message id: {}".format(discussion_message_id))

            for doc in cluster.docs:
                discussion_text = renderer.render_discussion_message(doc)
                client.send_discussion_message(discussion_text, discussion_message_id)
                sleep(0.3)

        print()
        if posted_clusters_path:
            posted_clusters.save(posted_clusters_path)
            print("{} clusters saved to file".format(len(posted_clusters)))
        posted_clusters.save_to_mongo(mongo_config_path)
        print("{} clusters saved to Mongo".format(len(posted_clusters)))
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", type=str, default=None)
    parser.add_argument("--documents-offset", type=int, default=9 * 3600)
    parser.add_argument("--channels-info-path", type=str, default="channels.json")
    parser.add_argument("--mongo-config-path", type=str, default="configs/mongo_config.json")
    parser.add_argument("--posted-clusters-path", type=str, default=None)
    parser.add_argument("--client-config-path", type=str, default="configs/client_config.json")
    parser.add_argument("--annotator-config-path", type=str, default="configs/annotator_config.json")
    parser.add_argument("--clusterer-config-path", type=str, default="configs/clusterer_config.json")
    parser.add_argument("--renderer-config-path", type=str, default="configs/renderer_config.json")
    args = parser.parse_args()
    main(**vars(args))
