import sys
import csv
import datetime
import random
from collections import Counter
from tqdm.auto import tqdm

from nyan.util import write_jsonl

def preprocess(text):
    text = str(text).strip().replace("\n", " ").replace("\xa0", " ")
    return text


def parse_lenta(input_file, output_file, use_preprocess=True):
    parts = {
        "экономика": 0.003,
        "спорт": 0.004,
        "наука": 0.01,
        "технологии": 0.01,
        "конфликты": 0.05,
        "происшествия": 0.005,
        "политика": 0.01,
        "развлечения": 0.05,
        "в мире": 0.005,
        "другое": 0.03
    }
    topics_mapping = {
        "Экономика": "экономика",
        "Спорт": "спорт",
        "Бизнес": "экономика",
        "Культпросвет": "развлечения",
        ("Наука и техника", "Игры"): "развлечения",
        ("Наука и техника", "Наука"): "наука",
        ("Наука и техника", "Космос"): "наука",
        ("Наука и техника", "Гаджеты"): "технологии",
        ("Наука и техника", "Софт"): "технологии",
        ("Наука и техника", "Техника"): "технологии",
        ("Мир", "Политика"): "в мире",
        ("Мир", "Происшествия"): "происшествия",
        ("Мир", "Конфликты"): "конфликты",
        ("Мир", "Преступность"): "происшествия",
        ("Россия", "Политика"): "политика",
        ("Россия", "Происшествия"): "происшествия",
        ("Интернет и СМИ", "Мемы"): "технологии",
        ("Интернет и СМИ", "Киберпреступность"): "технологии",
        ("Интернет и СМИ", "Интернет"): "технологии",
        ("Интернет и СМИ", "Вирусные ролики"): "технологии",
        ("Ценности", "Стиль"): "другое",
        ("Ценности", "Явления"): "другое",
        ("Из жизни", "Происшествия"): "происшествия",
        ("Путешествия", "Происшествия"): "происшествия",
    }
    with open(input_file, "r") as r:
        next(r)
        reader = csv.reader(r, delimiter=',')
        records = []
        border_date = datetime.datetime.strptime("2010/01/01", '%Y/%m/%d')
        for row in tqdm(reader):
            url, title, text, topic, tag, date = row
            date = datetime.datetime.strptime(date, '%Y/%m/%d')
            if date < border_date:
                continue
            topic = topic.strip()
            tag = tag.strip()
            true_topic = None
            if topic in topics_mapping:
                true_topic = topics_mapping[topic]
            elif (topic, tag) in topics_mapping:
                true_topic = topics_mapping[(topic, tag)]
            else:
                continue
            if use_preprocess:
                title = preprocess(title)
                text = preprocess(text)
            records.append({"url": url, "text": title + " " + text, "result": true_topic})
        print(len(records))
        records = [r for r in records if random.random() <= parts[r["result"]]]
        print(len(records))
        rub_cnt = Counter()
        for d in records:
            rub_cnt[d["result"]] += 1
        print(rub_cnt.most_common())
        write_jsonl(output_file, records)

input_path = sys.argv[1]
output_path = sys.argv[2]
parse_lenta(input_path, output_path)
