import pytest
from typing import List, Dict

from nyan.annotator import Annotator
from nyan.document import read_documents_file, Document
from nyan.clusterer import Clusterer
from nyan.ranker import Ranker
from nyan.renderer import Renderer
from nyan.channels import Channels


def get_channels_info_path() -> str:
    return "channels.json"


@pytest.fixture
def channels_info_path() -> str:
    return get_channels_info_path()


def get_annotator_config_path() -> str:
    return "configs/annotator_config.json"


@pytest.fixture
def annotator_config_path() -> str:
    return get_annotator_config_path()


def get_input_path() -> str:
    return "tests/data/input_docs.jsonl"


@pytest.fixture
def input_path() -> str:
    return get_input_path()


def get_output_path() -> str:
    return "tests/data/output_docs.jsonl"


@pytest.fixture
def output_path() -> str:
    return get_output_path()


@pytest.fixture
def clusterer_config_path() -> str:
    return "configs/clusterer_config.json"


@pytest.fixture
def renderer_config_path() -> str:
    return "configs/renderer_config.json"


@pytest.fixture
def ranker_config_path() -> str:
    return "configs/ranker_config.json"


@pytest.fixture
def channels(channels_info_path) -> Channels:
    return Channels(channels_info_path)


@pytest.fixture
def annotator(annotator_config_path, channels) -> Annotator:
    return Annotator(annotator_config_path, channels)


@pytest.fixture
def clusterer(clusterer_config_path) -> Clusterer:
    return Clusterer(clusterer_config_path)


@pytest.fixture
def ranker(ranker_config_path) -> Ranker:
    return Ranker(ranker_config_path)


@pytest.fixture
def renderer(renderer_config_path, channels) -> Renderer:
    return Renderer(renderer_config_path, channels)


@pytest.fixture
def input_docs(input_path) -> List[Document]:
    return read_documents_file(input_path)


@pytest.fixture
def output_docs(output_path) -> List[Document]:
    return read_documents_file(output_path)
