from typing import List, Dict
from dataclasses import fields

import pytest
import numpy as np
import pytest_check as check

from nyan.annotator import Annotator
from nyan.document import read_documents_file, Document
from nyan.clusterer import Clusterer
from nyan.ranker import Ranker
from nyan.fasttext import FasttextClassifier
from nyan.renderer import Renderer
from nyan.channels import Channels
from nyan.clusters import Clusters
from nyan.util import read_jsonl


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


def get_annotator_output_path() -> str:
    return "tests/data/output_docs.jsonl"


@pytest.fixture
def annotator_output_path() -> str:
    return get_annotator_output_path()


@pytest.fixture
def lang_detector() -> FasttextClassifier:
    return FasttextClassifier("models/lid.176.bin")


def get_ranker_output_path() -> str:
    return "tests/data/output_clusters.jsonl"


@pytest.fixture
def ranker_output_path() -> str:
    return get_ranker_output_path()


def get_clusterer_config_path() -> str:
    return "configs/clusterer_config.json"


@pytest.fixture
def clusterer_config_path() -> str:
    return get_clusterer_config_path()


def get_ranker_config_path() -> str:
    return "configs/test_ranker_config.json"


@pytest.fixture
def ranker_config_path() -> str:
    return get_ranker_config_path()


def get_renderer_config_path() -> str:
    return "configs/renderer_config.json"


@pytest.fixture
def renderer_config_path() -> str:
    return get_renderer_config_path()


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
def output_docs(annotator_output_path) -> List[Document]:
    return read_documents_file(annotator_output_path)


@pytest.fixture
def output_clusters(ranker_output_path) -> Clusters:
    return Clusters.load(ranker_output_path)


@pytest.fixture
def compare_docs():
    def _compare_docs(
        predicted_doc: Document,
        canonical_doc: Document,
        is_short: bool = False
    ):
        purl = predicted_doc.url
        curl = canonical_doc.url
        assert purl == curl, f"Different docs: {purl} vs {curl}"
        pred_dict = predicted_doc.asdict(is_short=is_short)
        canon_dict = canonical_doc.asdict(is_short=is_short)
        diff = {}
        for key, pred_value in pred_dict.items():
            canon_value = canon_dict[key]
            if key == "embedding":
                np.testing.assert_allclose(pred_value, canon_value, atol=0.0001)
                continue
            if key == "category_scores":
                for key, p in pred_value.items():
                    c = canon_value[key]
                    np.testing.assert_almost_equal(p, c, err_msg="{}: {} vs {}".format(key, p, c))
            if pred_value != canon_value:
                diff[key] = (pred_value, canon_value)
        check.is_false(diff, f"Diff in keys {','.join(diff.keys())} in doc '{curl}'")
        for key, (pv, cv) in diff.items():
            check.is_true(False, f"Diff in '{key}': '{pv}' vs canonical '{cv}'")
        return diff
    return _compare_docs


@pytest.fixture
def clip_data() -> List[Dict[str, str]]:
    return list(read_jsonl("tests/data/clip.jsonl"))
