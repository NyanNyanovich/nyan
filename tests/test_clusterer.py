import pytest
from typing import List

from nyan.annotator import Annotator
from nyan.clusterer import Clusterer
from nyan.document import Document


def test_clusterer_on_snapshot(
    annotator: Annotator,
    clusterer: Clusterer,
    input_docs: List[Document]
):
    docs = annotator(input_docs)
    clusters = clusterer(docs)
    assert len(clusters) == 3
