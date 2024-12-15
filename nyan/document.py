import os
from typing import List, Tuple, Dict, Any, Optional, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from tqdm import tqdm

from nyan.mongo import get_documents_collection, get_annotated_documents_collection
from nyan.util import Serializable


CURRENT_VERSION = 6


@dataclass
class Document(Serializable):
    url: str
    channel_id: str
    post_id: int
    views: int
    pub_time: int
    pub_time_dt: Optional[datetime] = None
    text: Optional[str] = None
    fetch_time: Optional[int] = None
    images: Sequence[str] = tuple()
    links: Sequence[str] = tuple()
    videos: Sequence[str] = tuple()
    reply_to: Optional[str] = None
    forward_from: Optional[str] = None

    channel_title: str = ""
    has_obscene: bool = False
    patched_text: Optional[str] = None
    groups: Dict[str, str] = field(default_factory=dict)
    issue: Optional[str] = None
    language: Optional[str] = None
    category: Optional[str] = None
    category_scores: Dict[str, float] = field(default_factory=dict)
    tokens: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_key: str = "multilingual_e5_base"
    embedded_images: Sequence[Dict[str, Any]] = tuple()

    version: int = CURRENT_VERSION

    def is_reannotation_needed(self, new_doc: "Document") -> bool:
        assert new_doc.url == self.url
        if self.version != CURRENT_VERSION:
            return True
        return new_doc.text != self.text

    def is_discarded(self) -> bool:
        if self.issue is None:
            return True
        if self.groups is None:
            return True
        if not self.patched_text or len(self.patched_text) < 12:
            return True
        return self.category == "not_news"

    def update_meta(self, new_doc: "Document") -> None:
        self.fetch_time = new_doc.fetch_time
        self.views = new_doc.views

    def asdict(self, is_short: bool = False) -> Dict[str, Any]:
        record = super().asdict()
        if is_short:
            record.pop("text")
            record.pop("embedding")
            record.pop("embedded_images")
        return record

    @property
    def cropped_text(self, max_words_count: int = 50) -> str:
        if not self.patched_text:
            return ""
        words = self.patched_text.split()
        if len(words) < max_words_count:
            return " ".join(words)
        return " ".join(words[:max_words_count]) + "..."


def read_documents_file(
    file_path: str, current_ts: Optional[int] = None, offset: Optional[int] = None
) -> List[Document]:
    assert os.path.exists(file_path)
    with open(file_path) as r:
        docs = [Document.deserialize(line) for line in r]
        if current_ts and offset:
            docs = [doc for doc in docs if doc.pub_time >= current_ts - offset]
    return docs


def read_documents_mongo(
    mongo_config_path: str, current_ts: int, offset: int
) -> List[Document]:
    collection = get_documents_collection(mongo_config_path)
    docs = list(collection.find({"pub_time": {"$gte": current_ts - offset}}))
    return [Document.fromdict(doc) for doc in docs]


def read_annotated_documents_mongo(
    mongo_config_path: str, docs: List[Document]
) -> Tuple[List[Document], List[Document]]:
    collection = get_annotated_documents_collection(mongo_config_path)
    annotated_docs = []
    remaining_docs = []
    for doc in tqdm(docs, desc="Reading annotated docs from Mongo"):
        annotated_doc = collection.find_one({"url": doc.url})
        if not annotated_doc:
            remaining_docs.append(doc)
            continue

        annotated_doc_loaded: Document = Document.fromdict(annotated_doc)
        if annotated_doc_loaded.is_reannotation_needed(doc):
            remaining_docs.append(doc)
            continue

        annotated_doc_loaded.update_meta(doc)
        assert annotated_doc_loaded.embedding is not None
        assert annotated_doc_loaded.patched_text is not None
        annotated_docs.append(annotated_doc_loaded)
    return annotated_docs, remaining_docs


def write_annotated_documents_mongo(
    mongo_config_path: str, docs: List[Document]
) -> None:
    collection = get_annotated_documents_collection(mongo_config_path)

    indices = collection.index_information()
    if "url_1" not in indices:
        collection.create_index([("url", 1)], name="url_1")

    for doc in docs:
        assert doc.embedding is not None
        assert doc.patched_text is not None
        collection.replace_one({"url": doc.url}, doc.asdict(), upsert=True)
