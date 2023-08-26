import argparse
import random
import requests
import json
import time
from datetime import datetime

from jinja2 import Template

from nyan.clusters import Clusters
from nyan.client import TelegramClient
from nyan.renderer import Renderer
from nyan.util import get_current_ts, ts_to_dt, gen_batch
from nyan.openai import openai_completion
from nyan.mongo import get_memes_collection

MEMEGEN_HOST = "https://api.memegen.link"
ALL_MEME_TEMPLATES = requests.get(f"{MEMEGEN_HOST}/templates").json()


def get_memegen_meme(
    clusters,
    all_templates,
    prompt_path,
    model_name,
    templates_count
):
    with open(prompt_path) as f:
        template = Template(f.read())

    meme_templates = random.sample(all_templates, templates_count)
    prompt = template.render(
        clusters=clusters,
        meme_templates=meme_templates
    ).strip() + "\n"
    print(prompt)

    messages = [{"role": "user", "content": prompt}]
    result = openai_completion(messages=messages, model_name=model_name)
    content = result.message.content.strip()
    print(content)

    content = content[content.find("{"):content.rfind("}") + 1]
    response = json.loads(content)
    assert "image_url" in response
    assert "explanation" in response
    assert "post_urls" in response

    response["image_url"] += "?font=impact"
    if "localhost" in response["image_url"]:
        response["image_url"] = response["image_url"].replace("http://localhost:5000", MEMEGEN_HOST)

    return response


def main(
    mongo_config_path,
    client_config_path,
    duration_hours,
    max_news_count,
    issue_name,
    target_issue_name,
    prompt_path,
    html_template_path,
    model_name,
    auto,
    templates_count,
    load_offset
):
    random.seed(time.time())
    collection = get_memes_collection(mongo_config_path)
    current_ts = get_current_ts()
    existing_memes = list(collection.find({"create_time": {"$gte": current_ts - load_offset}}))
    used_clids = {r["clid"] for r in existing_memes}
    used_templates = {r["template_id"] for r in existing_memes}

    duration = int(duration_hours * 3600)
    clusters = Clusters.load_from_mongo(mongo_config_path, get_current_ts(), duration)
    clusters = list(clusters.clid2cluster.values())
    clusters = [cl for cl in clusters if cl.clid not in used_clids]
    clusters.sort(key=lambda cl: cl.create_time)
    fixed_clusters = []
    for cluster in clusters:
        messages = [m for m in cluster.messages if m.issue == issue_name]
        if not messages:
            continue
        message = messages[0]
        fixed_clusters.append({
            "text": cluster.annotation_doc.patched_text,
            "url": f"https://t.me/nyannews/{message.message_id}",
            "clid": cluster.clid
        })
    clusters = fixed_clusters
    clusters = clusters[-max_news_count:]

    all_templates = ALL_MEME_TEMPLATES
    all_templates = [t for t in all_templates if t["id"] not in used_templates]
    response = get_memegen_meme(
        clusters,
        all_templates=all_templates,
        prompt_path=prompt_path,
        model_name=model_name,
        templates_count=templates_count
    )
    print("Response:", response)
    with open(html_template_path, "r") as f:
        template = Template(f.read())
        text = template.render(**response)

    url = response["post_urls"][0]
    clid = [cl for cl in clusters if cl["url"] == url][0]["clid"]

    should_publish = False
    if not auto:
        should_publish = input("Publish? y/n ").strip() == "y"

    image_url = response["image_url"]
    template_id = image_url.replace("://", "").split("/")[2]
    animations, photos = tuple(), tuple()
    if ".gif" in image_url:
        animations = [image_url]
    else:
        photos = [image_url]

    record = {
        "clusters": clusters,
        "response": response,
        "template_id": template_id,
        "clid": clid,
        "was_published": False,
        "create_time": current_ts
    }
    print(record)

    if auto or should_publish:
        client = TelegramClient(client_config_path)
        client.send_message(
            text,
            photos=photos,
            animations=animations,
            issue_name=target_issue_name,
            parse_mode="html"
        )
        record["was_published"] = True

    collection.insert_one(record)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--duration-hours", type=int, default=6)
    parser.add_argument("--load-offset", type=int, default=3600 * 72)
    parser.add_argument("--max-news-count", type=int, default=4)
    parser.add_argument("--templates-count", type=int, default=10)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--target-issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, default="nyan/prompts/memegen.txt")
    parser.add_argument("--html-template-path", type=str, default="nyan/templates/meme.txt")
    parser.add_argument("--model-name", type=str, default="gpt-4")
    parser.add_argument("--auto", default=False, action="store_true")
    args = parser.parse_args()
    main(**vars(args))
