def test_lang_detector(lang_detector):
    texts = {
        "ru": [
            "Спасатели продолжают тушить пожар.",
            "Сообщения о сбитии ракет X-22, которые случались в прошлом, были ошибочными."
        ],
        "uk": [
            "Рятувальники продовжують гасити пожежу.",
            "Повідомлення про збиті ракети Х-22 у минулому були помилковими."
        ],
        "en": [
            "Rescuers continue to extinguish the fire.",
            "Reports of downed Kh-22 missiles in the past were false."
        ]
    }

    for lang, samples in texts.items():
        for sample in samples:
            pred_lang, _ = lang_detector(sample)
            assert pred_lang == lang, f"{lang} vs {pred_lang}, {sample}"
