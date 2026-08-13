import json

from nyan.ads import AdRemover, compute_overlap
from nyan.openai import LLM


ORIGINAL = (
    "Мэрия Москвы сообщила о закрытии участка Сокольнической линии "
    "с 12 по 14 августа. Поезда будут ходить в обычном режиме на остальных "
    "участках, для пассажиров запустят компенсационные автобусы.\n"
    "Подпишись — | Мы в MAX."
)
CLEANED = (
    "Мэрия Москвы сообщила о закрытии участка Сокольнической линии "
    "с 12 по 14 августа. Поезда будут ходить в обычном режиме на остальных "
    "участках, для пассажиров запустят компенсационные автобусы."
)


def get_renderer_config_path() -> str:
    return "configs/renderer_config.json"


def make_ad_remover() -> AdRemover:
    with open(get_renderer_config_path()) as r:
        config = json.load(r)
    return AdRemover(config["ad_remover"], LLM(config={"model_name": "test"}))


def test_compute_overlap_on_pure_deletion():
    kept_ratio, new_ratio = compute_overlap(ORIGINAL, CLEANED)
    assert new_ratio == 0.0
    assert 0.85 < kept_ratio < 1.0


def test_compute_overlap_on_rewrite():
    rewritten = "В Москве на три дня закроют участок красной ветки метро."
    _, new_ratio = compute_overlap(ORIGINAL, rewritten)
    assert new_ratio > 0.1


def test_validate_accepts_ad_removal():
    ad_remover = make_ad_remover()
    assert ad_remover.validate(ORIGINAL, CLEANED) == CLEANED


def test_validate_accepts_unchanged_text():
    ad_remover = make_ad_remover()
    assert ad_remover.validate(ORIGINAL, ORIGINAL) == ORIGINAL


def test_validate_rejects_rewritten_text():
    ad_remover = make_ad_remover()
    rewritten = CLEANED.replace("Мэрия Москвы", "Власти столицы")
    assert ad_remover.validate(ORIGINAL, rewritten) is None


def test_validate_accepts_big_relative_cut_on_short_post():
    ad_remover = make_ad_remover()
    original = (
        "Госдума приняла закон о новых правилах перевозки животных.\n"
        "Дождь выбрал главное — читайте материал на нашем сайте."
    )
    cleaned = "Госдума приняла закон о новых правилах перевозки животных."
    assert ad_remover.validate(original, cleaned) == cleaned


def test_validate_rejects_summarized_text():
    ad_remover = make_ad_remover()
    summarized = "Мэрия Москвы сообщила о закрытии участка Сокольнической линии"
    assert ad_remover.validate(ORIGINAL, summarized) is None


def test_validate_rejects_empty_text():
    ad_remover = make_ad_remover()
    assert ad_remover.validate(ORIGINAL, "") is None
