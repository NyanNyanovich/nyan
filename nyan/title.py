from typing import List
from statistics import mean

from scipy.spatial.distance import cosine  # type: ignore

from nyan.document import Document
import nyan.config as config

def filter_ru_only(doc: Document) -> bool:
    return doc.language == "ru"


def filter_not_obscene(doc: Document) -> bool:
    return not doc.has_obscene


def filter_not_long(doc: Document) -> bool:
    if not doc.text:
        return False
    return len(doc.text) < 500


def filter_fresh(doc: Document) -> bool:
    if not doc.fetch_time or not doc.pub_time:
        return False
    return abs(doc.fetch_time - doc.pub_time) < 3600


def filter_purple(doc: Document) -> bool:
    return doc.groups["main"] == "purple"


def choose_title(docs: List[Document], issues: List[str]) -> Document:
    assert docs

    avg_distances = dict()
    for doc1 in docs:
        distances = [cosine(doc1.embedding, doc2.embedding) for doc2 in docs]
        avg_distances[doc1.url] = mean(distances)

    hard_filters = (
        filter_ru_only if config.FILTER_TITILE_RU_ONLY else lambda x: True, 
        filter_not_obscene if config.FILTER_TITILE_OBSCENE else lambda x: True,  
        filter_fresh
    )
    for flt in hard_filters:
        filtered_docs = list(filter(flt, docs))
        if filtered_docs:
            docs = filtered_docs

    # Choosing documents specific for issues
    issue_filters = []
    possible_issues = set(docs[0].groups.keys())
    for issue in issues:
        if issue == "main":
            continue
        if issue not in possible_issues:
            continue
        # Double lambda to capture "issue" properly
        issue_filter = (lambda x: lambda doc: doc.groups.get(x) == x)(issue)
        issue_filters.append(issue_filter)

    soft_filters = [filter_not_long] + issue_filters + [filter_purple]

    for f in soft_filters:
        if not f:
            continue
        filtered_docs = list(filter(f, docs))
        if len(filtered_docs) >= 2:
            docs = filtered_docs

    return min(docs, key=lambda x: avg_distances[x.url])
