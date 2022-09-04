import pytest
from typing import List

from nyan.annotator import Annotator
from nyan.document import Document


def test_annotator_on_snapshot(
    annotator: Annotator,
    input_docs: List[Document],
    output_docs: List[Document]
):
    docs = annotator(input_docs)
    for doc in docs:
        doc.embedding = None

    for predicted_doc, canonical_doc in zip(docs, output_docs):
        assert predicted_doc.serialize() == canonical_doc.serialize()
