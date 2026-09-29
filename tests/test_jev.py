import json
import os

import pytest
from dotenv import load_dotenv

from nyan.jev import JevClassifierHead
from nyan.openai import DOTENV_PATH
from tests.conftest import get_annotator_config_path

load_dotenv(DOTENV_PATH)

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY is not set, Jev is served through OpenRouter",
)

AD = (
    "Друзья, только до конца недели скидка 50% на наш курс по digital-маркетингу! "
    "Регистрируйтесь по ссылке в закрепе и забирайте бонусы."
)
WAR = (
    "Минобороны сообщило об ударе по позициям ВСУ в Херсонской области, "
    "уничтожены две гаубицы и склад боеприпасов."
)


@pytest.fixture
def jev_head() -> JevClassifierHead:
    with open(get_annotator_config_path()) as r:
        config = json.load(r)
    return JevClassifierHead(config["jev_cat_detector"])


def test_jev_classifier_head(jev_head: JevClassifierHead):
    ad_category, ad_scores = jev_head(AD)
    war_category, war_scores = jev_head(WAR)
    assert set(ad_scores) == set(jev_head.criteria)
    assert abs(sum(ad_scores.values()) - 1.0) < 0.05
    assert ad_category == "not_news"
    assert war_category == "war"


def test_jev_classify_many_falls_back_on_failure(jev_head: JevClassifierHead):
    jev_head.client.api_url = jev_head.client.api_url + "-nonexistent"
    jev_head.client.retries = 1
    jev_head.client.sleep_time = 0.0
    assert jev_head.classify_many([AD, WAR]) == [None, None]
