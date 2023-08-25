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


ALL_MEME_TEMPLATES = requests.get("https://api.memegen.link/templates").json()


def get_memegen_meme(
    clusters,
    prompt_path,
    model_name,
    templates_count
):
    with open(prompt_path) as f:
        template = Template(f.read())

    meme_templates = random.sample(ALL_MEME_TEMPLATES, templates_count)

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
    url = response["url"] + "?font=impact"
    explanation = response["explanation"]
    return url, explanation


def main(
    mongo_config_path,
    client_config_path,
    duration_hours,
    max_news_count,
    issue_name,
    target_issue_name,
    prompt_path,
    template_path,
    model_name,
    auto,
    templates_count
):
    duration = int(duration_hours * 3600)
    clusters = Clusters.load_from_mongo(mongo_config_path, get_current_ts(), duration)
    clusters = list(clusters.clid2cluster.values())
    clusters.sort(key=lambda cl: cl.create_time)
    fixed_clusters = []
    for cluster in clusters:
        messages = [m for m in cluster.messages if m.issue == issue_name]
        if not messages:
            continue
        fixed_clusters.append(cluster)
    clusters = fixed_clusters
    clusters = clusters[-max_news_count:]

    image_url, explanation = get_memegen_meme(
        clusters,
        prompt_path=prompt_path,
        model_name=model_name,
        templates_count=templates_count
    )
    print("URL:", image_url)
    with open(template_path, "r") as f:
        template = Template(f.read())
    text = template.render(explanation=explanation)

    should_publish = False
    if not auto:
        should_publish = input("Publish? y/n ").strip() == "y"

    client = TelegramClient(client_config_path)
    if auto or should_publish:
        client.send_message(
            text,
            photos=[image_url],
            issue_name=target_issue_name,
            parse_mode="html"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--duration-hours", type=int, default=12)
    parser.add_argument("--max-news-count", type=int, default=5)
    parser.add_argument("--templates-count", type=int, default=5)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--target-issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, required=True)
    parser.add_argument("--template-path", type=str, required=True)
    parser.add_argument("--model-name", type=str, default="gpt-4")
    parser.add_argument("--auto", default=False, action="store_true")
    args = parser.parse_args()
    main(**vars(args))
