import json

from tests.conftest import (
    get_input_path,
    get_annotator_output_path,
    get_ranker_output_path,
    get_annotator_config_path,
    get_channels_info_path,
    get_clusterer_config_path,
    get_ranker_config_path
)
from nyan.annotator import Annotator
from nyan.channels import Channels
from nyan.clusterer import Clusterer
from nyan.ranker import Ranker
from nyan.document import read_documents_file, Document

annotator = Annotator(get_annotator_config_path(), Channels(get_channels_info_path()))
clusterer = Clusterer(get_clusterer_config_path())
ranker = Ranker(get_ranker_config_path())

docs = read_documents_file(get_input_path())
docs = list(annotator(docs))
docs = annotator.postprocess(docs)
with open(get_annotator_output_path(), "w") as w:
    for doc in docs:
        w.write(doc.serialize() + "\n")

clusters = clusterer(docs)
clusters = ranker(clusters)
with open(get_ranker_output_path(), "w") as w:
    for cluster in clusters:
        w.write(cluster.serialize() + "\n")
