import sys
import json

from pymongo import MongoClient

output_path = sys.argv[1]
assert output_path, "Provide output path!"

with open("configs/prod_mongo_config.json") as r:
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
