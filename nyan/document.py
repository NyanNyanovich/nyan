import json
import os
from typing import List, Tuple
from dataclasses import dataclass

from nyan.mongo import get_documents_collection
from nyan.util import Serializable


@dataclass
class Document(Serializable):
    url: str
    channel_id: str
    post_id: int
    text: str
    views: int
    pub_time: int
    has_obscene: bool = False
    channel_title: str = ""
    fetch_time: int = None
    language: str = None
    category: str = None
    group: str = None
    tokens: str = None
    embedding: List[float] = None
    images: List[str] = None
    links: List[str] = tuple()
    videos: List[str] = tuple()
    reply_to: str = None
    forward_from: str = None

    not_serializing: Tuple[str] = ("embedding", )


def read_documents_file(file_path, current_ts=None, offset=None):
    assert os.path.exists(file_path)
    with open(file_path) as r:
        docs = [Document.deserialize(line) for line in r]
        if current_ts and offset:
            docs = [doc for doc in docs if doc.pub_time >= current_ts - offset]
    return docs


def read_documents_mongo(mongo_config_path, current_ts, offset):
    collection = get_documents_collection(mongo_config_path)
    docs = list(collection.find({"pub_time": {"$gte": current_ts - offset}}))
    docs = [Document.fromdict(doc) for doc in docs]
    return docs
