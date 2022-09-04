import json
import os
from typing import List, Tuple, Dict
from dataclasses import dataclass

from nyan.mongo import get_documents_collection, get_annotated_documents_collection
from nyan.util import Serializable


@dataclass
class Document(Serializable):
    url: str
    channel_id: str
    post_id: int
    views: int
    pub_time: int
    text: str = None
    patched_text: str = None
    has_obscene: bool = False
    channel_title: str = ""
    fetch_time: int = None
    language: str = None
    category: str = None
    groups: Dict[str, str] = None
    issue: str = None
    tokens: str = None
    embedding: List[float] = None
    images: List[str] = None
    links: List[str] = tuple()
    videos: List[str] = tuple()
    reply_to: str = None
    forward_from: str = None

    not_serializing: Tuple[str] = tuple()

    def is_reannotation_needed(self, new_doc):
        assert new_doc.url == self.url
        if new_doc.text != self.text:
            return True
        return False

    def update_meta(self, new_doc):
        self.fetch_time = new_doc.fetch_time
        self.views = new_doc.views


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


def read_annotated_documents_mongo(mongo_config_path, docs):
    collection = get_annotated_documents_collection(mongo_config_path)
    annotated_docs = []
    remaining_docs = []
    for doc in docs:
        annotated_doc = collection.find_one({"url": doc.url})
        if not annotated_doc:
            remaining_docs.append(doc)
            continue

        annotated_doc = Document.fromdict(annotated_doc)
        if annotated_doc.is_reannotation_needed(doc):
            remaining_docs.append(doc)
            continue

        annotated_doc.update_meta(doc)
        assert annotated_doc.embedding is not None
        assert annotated_doc.patched_text is not None
        annotated_docs.append(annotated_doc)
    return annotated_docs, remaining_docs


def write_annotated_documents_mongo(mongo_config_path, docs):
    collection = get_annotated_documents_collection(mongo_config_path)
    for doc in docs:
        assert doc.embedding is not None
        assert doc.patched_text is not None
        collection.replace_one({"url": doc.url}, doc.asdict(), upsert=True)

