import pytest
from typing import List, Callable

from nyan.annotator import Annotator
from nyan.document import Document


def test_annotator_on_snapshot(
    annotator: Annotator,
    input_docs: List[Document],
    output_docs: List[Document],
    compare_docs: Callable
):
    docs = annotator(input_docs)
    for predicted_doc, canonical_doc in zip(docs, output_docs):
        compare_docs(predicted_doc, canonical_doc)
