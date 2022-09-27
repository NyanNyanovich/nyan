from typing import List
from statistics import mean

from scipy.spatial.distance import cosine

from nyan.document import Document


def filter_ru_only(doc):
    return doc.language == "ru"


def filter_not_obscene(doc):
    return not doc.has_obscene


def filter_not_long(doc):
    return len(doc.text) < 500


def filter_fresh(doc):
    return abs(doc.fetch_time - doc.pub_time) < 3600


def filter_purple(doc):
    return doc.groups["main"] == "purple"


def filter_tech(doc):
    return doc.groups["tech"] == "tech"


def choose_title(docs: List[Document], issue: str):
    avg_distances = dict()
    for doc1 in docs:
        distances = [cosine(doc1.embedding, doc2.embedding) for doc2 in docs]
        avg_distances[doc1.url] = mean(distances)

    hard_filters = (
        filter_ru_only,
        filter_not_obscene,
        filter_fresh
    )
    for f in hard_filters:
        if not f:
            continue
        filtered_docs = list(filter(f, docs))
        if filtered_docs:
            docs = filtered_docs

    soft_filters = (
        filter_not_long,
        filter_tech if issue == "tech" else None,
        filter_purple
    )
    for f in soft_filters:
        if not f:
            continue
        filtered_docs = list(filter(f, docs))
        if len(filtered_docs) >= 2:
            docs = filtered_docs

    return min(docs, key=lambda x: avg_distances[x.url])
