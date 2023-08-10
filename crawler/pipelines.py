import json
from collections import defaultdict

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from pymongo import MongoClient


def check_item(item):
    adapter = ItemAdapter(item)
    required_fields = ("url", "text", "pub_time", "views")
    for field in required_fields:
        value = adapter.get(field)
        if not value:
            raise DropItem(f"Missing {field} field in {item}")


class MongoPipeline:
    def open_spider(self, spider):
        with open("configs/mongo_config.json") as r:
            config = json.load(r)
        self.client = MongoClient(**config["client"])
        database_name = config["database_name"]
        documents_collection_name = config["documents_collection_name"]
        self.collection = self.client[database_name][documents_collection_name]

    def process_item(self, item, spider):
        check_item(item)
        adapter = ItemAdapter(item)
        url = adapter.get("url")
        self.collection.replace_one({"url": url}, adapter.asdict(), upsert=True)
        return item


class JsonlPipeline:
    def open_spider(self, spider):
        self.items = defaultdict(dict)

    def close_spider(self, spider):
        with open("telegram_news.jsonl", "w") as w:
            for _, item in self.items.items():
                w.write(json.dumps(item, ensure_ascii=False) + "\n")

    def process_item(self, item, spider):
        check_item(item)
        adapter = ItemAdapter(item)
        url = adapter.get("url")
        self.items[url] = adapter.asdict()
        return item
