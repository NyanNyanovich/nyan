import argparse
import json

from pymongo import MongoClient

from nyan.util import get_current_ts


def main(
    output_path,
    mongo_config,
    clid_start,
    clid_end,
    batch_size
):
    with open(mongo_config) as r:
        config = json.load(r)

    client = MongoClient(**config["client"])
    database_name = config["database_name"]
    clusters_collection_name = config["clusters_collection_name"]
    collection = client[database_name][clusters_collection_name]

    if not clid_start:
        first_cluster = collection.find_one(sort=[("clid", 1)])
        clid_start = first_cluster["clid"]
    if not clid_end:
        last_cluster = collection.find_one(sort=[("clid", -1)])
        clid_end = last_cluster["clid"] + 1
    print(f"Start clid: {clid_start}")
    print(f"End clid: {clid_end}")

    current_clid_start = clid_start
    with open(output_path, "w") as w:
        while current_clid_start < clid_end:
            print(clid_end - current_clid_start)
            current_clid_end = current_clid_start + batch_size
            clusters = list(collection.find({"clid": {"$gte": current_clid_start, "$lt": current_clid_end}}))
            clusters.sort(key=lambda x: x["annotation_doc"]["pub_time"])
            for cluster in clusters:
                if cluster["clid"] < clid_start:
                    continue
                if cluster["clid"] > clid_end:
                    continue
                cluster.pop("_id")
                cluster["annotation_doc"].pop("embedding", None)
                cluster["annotation_doc"].pop("embedded_images", None)
                w.write(json.dumps(cluster, ensure_ascii=False) + "\n")
            current_clid_start = current_clid_end


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, default="data/clusters.jsonl")
    parser.add_argument("--mongo-config", type=str, default="configs/mongo_config.json")
    parser.add_argument("--clid-start", type=int, default=None)
    parser.add_argument("--clid-end", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    main(**vars(args))
