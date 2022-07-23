import json

from tests.conftest import get_annotator_input_path, get_annotator_output_path
from tests.conftest import get_annotator_config_path, get_channels_info_path
from nyan.annotator import Annotator
from nyan.document import read_documents_file, Document

annotator = Annotator(get_annotator_config_path(), get_channels_info_path())

docs = read_documents_file(get_annotator_input_path())
docs = annotator(docs)
with open(get_annotator_output_path(), "w") as w:
    for doc in docs:
        w.write(doc.serialize() + "\n")
