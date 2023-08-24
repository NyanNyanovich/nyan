import argparse
import random
import requests
import json
from datetime import datetime

from jinja2 import Template

from nyan.clusters import Clusters
from nyan.client import TelegramClient
from nyan.renderer import Renderer
from nyan.util import get_current_ts, ts_to_dt, gen_batch
from nyan.openai import openai_completion


def create_meme_request(
    clusters,
    issue_name,
    prompt_path,
    duration_hours,
    model_name
):
    with open(prompt_path) as f:
        template = Template(f.read())

    prompt = template.render(clusters=clusters).strip() + "\n"
    print(prompt)

    messages = [{"role": "user", "content": prompt}]
    result = openai_completion(messages=messages, model_name=model_name)
    content = result.message.content.strip()
    print(content)

    content = content[content.find("{"):content.rfind("}") + 1]
    return json.loads(content)


def get_imgflip_meme(
    request,
    imgflip_config_path
):
    with open(imgflip_config_path) as r:
        config = json.load(r)
    request["username"] = config["username"]
    request["password"] = config["password"]

    if "boxes" in request:
        for i, box in enumerate(request.pop("boxes")):
            request[f"boxes[{i}][text]"] = box["text"]

    url = "https://api.imgflip.com/caption_image"
    response = requests.post(url, data=request)

    assert response.status_code == 200
    response = response.json()
    assert response["success"]
    return response["data"]["url"]


def main(
    mongo_config_path,
    client_config_path,
    imgflip_config_path,
    duration_hours,
    max_news_count,
    min_news_count,
    issue_name,
    prompt_path,
    template_path,
    model_name,
    auto
):
    duration = int(duration_hours * 3600)
    clusters = Clusters.load_from_mongo(mongo_config_path, get_current_ts(), duration)
    clusters = list(clusters.clid2cluster.values())
    if len(clusters) < min_news_count:
        return
    clusters.sort(key=lambda cl: cl.create_time)
    fixed_clusters = []
    for cluster in clusters:
        messages = [m for m in cluster.messages if m.issue == issue_name]
        if not messages:
            continue
        fixed_clusters.append(cluster)
    clusters = fixed_clusters
    clusters = clusters[-max_news_count:]

    request = create_meme_request(
        clusters,
        issue_name=issue_name,
        prompt_path=prompt_path,
        duration_hours=duration_hours,
        model_name=model_name
    )
    image_url = get_imgflip_meme(request, imgflip_config_path)
    print("URL:", image_url)
    with open(template_path, "r") as f:
        template = Template(f.read())
    text = template.render(image_url=image_url)

    should_publish = False
    if not auto:
        should_publish = input("Publish? y/n ").strip() == "y"

    client = TelegramClient(client_config_path)
    if auto or should_publish:
        client.send_message(text, photos=[image_url], issue_name=issue_name, parse_mode="html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--imgflip-config-path", type=str, required=True)
    parser.add_argument("--duration-hours", type=int, default=12)
    parser.add_argument("--max-news-count", type=int, default=10)
    parser.add_argument("--min-news-count", type=int, default=3)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, required=True)
    parser.add_argument("--template-path", type=str, required=True)
    parser.add_argument("--model-name", type=str, default="gpt-4")
    parser.add_argument("--auto", default=False, action="store_true")
    args = parser.parse_args()
    main(**vars(args))
