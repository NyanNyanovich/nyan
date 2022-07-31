from typing import List
from statistics import mean

from scipy.spatial.distance import cosine

from nyan.document import Document


def choose_title(docs: List[Document]):
    avg_distances = dict()
    for doc1 in docs:
        distances = [cosine(doc1.embedding, doc2.embedding) for doc2 in docs]
        avg_distances[doc1.url] = mean(distances)

    filtered_docs = [d for d in docs if d.language == "ru"]
    if filtered_docs:
        docs = filtered_docs

    filtered_docs = [d for d in docs if not d.has_obscene]
    if filtered_docs:
        docs = filtered_docs

    filtered_docs = [d for d in docs if len(d.text) < 500]
    if filtered_docs:
        docs = filtered_docs

    filtered_docs = [d for d in docs if abs(d.fetch_time - d.pub_time) < 3600]
    if filtered_docs:
        docs = filtered_docs

    filtered_docs = [d for d in docs if d.group == "purple"]
    if len(filtered_docs) >= 2:
        docs = filtered_docs
    return min(docs, key=lambda x: avg_distances[x.url])
