import json
from typing import Dict, Any

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection


def read_config(mongo_config_path: str) -> Dict[str, Any]:
    with open(mongo_config_path) as r:
        mongo_config: Dict[str, Any] = json.load(r)
    return mongo_config


def get_database(mongo_config: Dict[str, Any]) -> Database[Dict[str, Any]]:
    client: MongoClient[Dict[str, Any]] = MongoClient(**mongo_config["client"])
    database_name = mongo_config["database_name"]
    return client[database_name]


def get_documents_collection(mongo_config_path: str) -> Collection[Dict[str, Any]]:
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    documents_collection_name = mongo_config["documents_collection_name"]
    return database[documents_collection_name]


def get_annotated_documents_collection(
    mongo_config_path: str,
) -> Collection[Dict[str, Any]]:
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    annotated_documents_collection_name = mongo_config[
        "annotated_documents_collection_name"
    ]
    return database[annotated_documents_collection_name]


def get_clusters_collection(mongo_config_path: str) -> Collection[Dict[str, Any]]:
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    clusters_collection_name = mongo_config["clusters_collection_name"]
    return database[clusters_collection_name]


def get_memes_collection(mongo_config_path: str) -> Collection[Dict[str, Any]]:
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    memes_collection_name = mongo_config.get("memes_collection_name", "memes")
    return database[memes_collection_name]


def get_topics_collection(mongo_config_path: str) -> Collection[Dict[str, Any]]:
    mongo_config = read_config(mongo_config_path)
    database = get_database(mongo_config)
    topics_collection_name = mongo_config.get("topics_collection_name", "topics")
    return database[topics_collection_name]
