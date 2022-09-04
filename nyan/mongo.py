import json

from pymongo import MongoClient


def read_config(mongo_config_path):
    with open(mongo_config_path) as r:
        mongo_config = json.load(r)
    return mongo_config


def get_database(mongo_config):
    client = MongoClient(**mongo_config["client"])
    database_name = mongo_config["database_name"]
    return client[database_name]


def get_documents_collection(mongo_config_path):
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    documents_collection_name = mongo_config["documents_collection_name"]
    return database[documents_collection_name]


def get_annotated_documents_collection(mongo_config_path):
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    annotated_documents_collection_name = mongo_config["annotated_documents_collection_name"]
    return database[annotated_documents_collection_name]


def get_clusters_collection(mongo_config_path):
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    clusters_collection_name = mongo_config["clusters_collection_name"]
    return database[clusters_collection_name]
