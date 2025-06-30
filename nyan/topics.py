import argparse
import json
import logging
from typing import List, Dict, Any

from jinja2 import Template

from nyan.clusters import Clusters
from nyan.client import TelegramClient
from nyan.util import get_current_ts, ts_to_dt
from nyan.openai import openai_completion
from nyan.mongo import get_topics_collection


def extract_topics(
    clusters: List[Dict[str, Any]],
    issue_name: str,
    prompt_path: str,
    duration_hours: int,
    model_name: str,
) -> List[Dict[str, Any]]:
    with open(prompt_path) as f:
        template = Template(f.read())

    prompt = template.render(clusters=clusters).strip() + "\n"
    logging.info(prompt)

    messages = [{"role": "user", "content": prompt}]
    content = openai_completion(messages=messages, model_name=model_name)
    logging.info(content)

    content = content[content.find("{") : content.rfind("}") + 1]
    topics: List[Dict[str, Any]] = json.loads(content)["topics"]
    for topic in topics:
        titles = topic["titles"]
        final_titles = []
        for r in titles:
            link = "[{}]({})".format(r["verb"], r["url"])
            fixed_title = r["title"].replace(" " + r["verb"], " " + link, 1)
            if fixed_title == r["title"]:
                fixed_title = r["title"].replace(r["verb"], link, 1)
            if fixed_title == r["title"]:
                link = "[{}]({})".format(r["verb"].capitalize(), r["url"])
                fixed_title = fixed_title.replace(r["verb"].capitalize(), link, 1)
            final_titles.append(fixed_title)
        topic["titles"] = final_titles
    return topics


def main(
    mongo_config_path: str,
    client_config_path: str,
    duration_hours: int,
    max_news_count: int,
    min_news_count: int,
    issue_name: str,
    prompt_path: str,
    template_path: str,
    model_name: str,
    auto: bool,
) -> None:
    duration = int(duration_hours * 3600)
    clusters_obj = Clusters.load_from_mongo(
        mongo_config_path, get_current_ts(), duration
    )
    clusters = list(clusters_obj.clid2cluster.values())
    clusters.sort(key=lambda cl: cl.create_time if cl.create_time else 0)

    fixed_clusters = []
    for cluster in clusters:
        messages = [m for m in cluster.messages if m.issue == issue_name]
        if not messages:
            continue
        message = messages[0]
        date_str = ""
        if cluster.create_time:
            dt = ts_to_dt(cluster.create_time)
            date_str = dt.strftime("%B %d, %H:%M")
        fixed_clusters.append(
            {
                "url": f"https://t.me/nyannews/{message.message_id}",
                "dt": date_str,
                "views": cluster.views,
                "sources_count": len([doc.channel_title for doc in cluster.docs]),
                "text": cluster.annotation_doc.patched_text,
            }
        )

    if len(fixed_clusters) < min_news_count:
        logging.info("Not enough news")
        return
    fixed_clusters = fixed_clusters[-max_news_count:]

    topics = extract_topics(
        fixed_clusters,
        issue_name=issue_name,
        prompt_path=prompt_path,
        duration_hours=duration_hours,
        model_name=model_name,
    )

    with open(template_path, "r") as f:
        template = Template(f.read())
    text = template.render(topics=topics, duration_hours=int(duration_hours))
    logging.info(text)

    should_publish = False
    if not auto:
        should_publish = input("Publish? y/n ").strip() == "y"

    if auto or should_publish:
        client = TelegramClient(client_config_path)
        client.send_message(text, issue_name=issue_name, parse_mode="Markdown")
        client.send_message(text, issue_name="summary", parse_mode="Markdown")

    collection = get_topics_collection(mongo_config_path)
    record = {"clusters": fixed_clusters, "topics": topics}
    collection.insert_one(record)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--duration-hours", type=int, default=8)
    parser.add_argument("--max-news-count", type=int, default=30)
    parser.add_argument("--min-news-count", type=int, default=5)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, default="nyan/prompts/topics.txt")
    parser.add_argument(
        "--template-path", type=str, default="nyan/templates/topics.html"
    )
    parser.add_argument("--model-name", type=str, default="gpt-4o")
    parser.add_argument("--auto", default=False, action="store_true")
    args = parser.parse_args()
    main(**vars(args))
