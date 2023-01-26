import argparse
import json

from pymongo import MongoClient

from nyan.util import get_current_ts


def main(
    output_path,
    mongo_config
):
    with open(mongo_config) as r:
        config = json.load(r)

    client = MongoClient(**config["client"])
    database_name = config["database_name"]
    clusters_collection_name = config["clusters_collection_name"]
    collection = client[database_name][clusters_collection_name]

    clusters = list(collection.find({}))
    clusters.sort(key=lambda x: x["annotation_doc"]["pub_time"])
    with open(output_path, "w") as w:
        for cluster in clusters:
            cluster.pop("_id")
            cluster["annotation_doc"].pop("embedding", None)
            cluster["annotation_doc"].pop("embedded_images", None)
            w.write(json.dumps(cluster, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, default="data/clusters.jsonl")
    parser.add_argument("--mongo-config", type=str, default="configs/mongo_config.json")
    args = parser.parse_args()
    main(**vars(args))
