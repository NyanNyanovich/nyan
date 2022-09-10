import pytest
from typing import List
from dataclasses import fields

import numpy as np

from nyan.annotator import Annotator
from nyan.document import Document


def test_annotator_on_snapshot(
    annotator: Annotator,
    input_docs: List[Document],
    output_docs: List[Document]
):
    docs = annotator(input_docs)
    for predicted_doc, canonical_doc in zip(docs, output_docs):
        pred_dict = predicted_doc.asdict()
        canon_dict = canonical_doc.asdict()
        for key, pred_value in pred_dict.items():
            canon_value = canon_dict[key]
            if key == "embedding":
                np.testing.assert_allclose(pred_value, canon_value, rtol=0.05)
                continue
            assert pred_value == canon_value, f"Diff in '{key}', {pred_value} vs {canon_value}"
