import argparse
import json
import re

from nyan.mongo import get_topics_collection
from nyan.util import write_jsonl

URL_RE = re.compile(r"\[(.*)\]\((.*)\)")


def main(
    output_path,
    mongo_config
):
    collection = get_topics_collection(mongo_config)
    summaries = list(collection.find({}))

    headlines = []
    for summary in summaries:
        topics = summary["topics"]
        clusters = summary["clusters"]
        url2cluster = {cl["url"]: cl for cl in clusters}
        for topic in topics:
            titles = topic["titles"]
            for title in titles:
                groups = URL_RE.search(title).groups()
                if len(groups) < 2:
                    continue
                url = groups[1]
                link_text = groups[0]
                fixed_title = URL_RE.sub(link_text, title)
                cluster = url2cluster[url]
                text = cluster["text"]
                headlines.append({
                    "text": text,
                    "title": fixed_title
                })
    write_jsonl(output_path, headlines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, default="data/headlines.jsonl")
    parser.add_argument("--mongo-config", type=str, default="configs/mongo_config.json")
    args = parser.parse_args()
    main(**vars(args))
