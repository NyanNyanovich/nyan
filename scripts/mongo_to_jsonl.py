import argparse
import json

from pymongo import MongoClient

from nyan.util import get_current_ts


def main(
    output_path,
    mongo_config,
    annotated
):
    with open(mongo_config) as r:
        config = json.load(r)

    client = MongoClient(**config["client"])
    database_name = config["database_name"]
    if annotated:
        documents_collection_name = config["annotated_documents_collection_name"]
    else:
        documents_collection_name = config["documents_collection_name"]
    collection = client[database_name][documents_collection_name]

    first_doc = collection.find_one(sort=[("pub_time", 1)])
    ts_start = first_doc["pub_time"]
    print(f"Start timestamp: {ts_start}")
    ts_end = get_current_ts()
    print(f"End timestamp: {ts_end}")
    ts_step = 3600 * 48

    ts_current = ts_start
    with open(output_path, "w") as w:
        while ts_current < ts_end:
            print(ts_end - ts_current)
            ts_next = ts_current + ts_step
            documents = list(collection.find({"pub_time": {"$gte": ts_current, "$lt": ts_next}}))
            documents.sort(key=lambda x: x["pub_time"])
            for document in documents:
                document.pop("_id")
                w.write(json.dumps(document, ensure_ascii=False) + "\n")
            ts_current = ts_next


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, default="data/docs.jsonl")
    parser.add_argument("--annotated", action="store_true")
    parser.add_argument("--mongo-config", type=str, default="configs/mongo_config.json")
    args = parser.parse_args()
    main(**vars(args))
