import argparse
import json

from pymongo import MongoClient


def main(
    output_path,
    mongo_config
):
    with open(mongo_config) as r:
        config = json.load(r)

    client = MongoClient(**config["client"])
    database_name = config["database_name"]
    documents_collection_name = config["documents_collection_name"]
    collection = client[database_name][documents_collection_name]

    print(collection.count_documents({}))

    with open(output_path, "w") as w:
        documents = list(collection.find({}))
        documents.sort(key=lambda x: x["pub_time"])
        for document in documents:
            document.pop("_id")
            w.write(json.dumps(document, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, default="data/docs.jsonl")
    parser.add_argument("--mongo-config", type=str, default="configs/mongo_config.json")
    args = parser.parse_args()
    main(**vars(args))
