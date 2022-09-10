import pytest
from typing import List

from nyan.annotator import Annotator
from nyan.clusterer import Clusterer
from nyan.document import Document


def test_clusterer_on_snapshot(
    clusterer: Clusterer,
    output_docs: List[Document]
):
    clusters = clusterer(output_docs)
    assert len(clusters) > 1
