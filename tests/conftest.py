import pytest
from typing import List, Dict

from nyan.annotator import Annotator
from nyan.document import read_documents_file, Document


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


def get_annotator_input_path() -> str:
    return "tests/data/annotator_input.jsonl"


@pytest.fixture
def annotator_input_path() -> str:
    return get_annotator_input_path()


def get_annotator_output_path() -> str:
    return "tests/data/annotator_output.jsonl"


@pytest.fixture
def annotator_output_path() -> str:
    return get_annotator_output_path()


@pytest.fixture
def annotator(annotator_config_path, channels_info_path) -> Annotator:
    return Annotator(annotator_config_path, channels_info_path)


@pytest.fixture
def annotator_input(annotator_input_path) -> List[Document]:
    return read_documents_file(annotator_input_path)


@pytest.fixture
def annotator_output(annotator_output_path) -> List[Document]:
    return read_documents_file(annotator_output_path)
