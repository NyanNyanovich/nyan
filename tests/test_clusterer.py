import pytest
from typing import List, Callable

from nyan.annotator import Annotator
from nyan.clusterer import Clusterer
from nyan.ranker import Ranker
from nyan.document import Document
from nyan.clusters import Clusters


def test_clusterer_and_ranker_on_snapshot(
    clusterer: Clusterer,
    ranker: Ranker,
    output_docs: List[Document],
    output_clusters: Clusters,
    compare_docs: Callable
):
    clusters = clusterer(output_docs)
    assert len(clusters) > 1

    filtered_clusters = ranker(clusters)
    assert len(filtered_clusters) >= 1

    for pcl, (_, ccl) in zip(filtered_clusters, sorted(output_clusters.clid2cluster.items())):
        compare_docs(pcl.annotation_doc, ccl.annotation_doc, is_short=True)
