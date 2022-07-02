import pytest
from typing import List

from nyan.annotator import Annotator
from nyan.document import Document


def test_annotator_on_snapshot(
    annotator: Annotator,
    annotator_input: List[Document],
    annotator_output: List[Document]
):
    docs = annotator(annotator_input)

    for predicted_doc, canonical_doc in zip(docs, annotator_output):
        assert predicted_doc.serialize() == canonical_doc.serialize()
