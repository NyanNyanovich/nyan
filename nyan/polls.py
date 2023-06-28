import argparse
import random
import json
from datetime import datetime

from jinja2 import Template

from nyan.clusters import Clusters
from nyan.channels import Channels
from nyan.client import TelegramClient
from nyan.renderer import Renderer
from nyan.util import get_current_ts, ts_to_dt, gen_batch
from nyan.openai import openai_completion


def make_poll(
    clusters,
    issue_name,
    prompt_path,
    duration_hours,
    model_name
):
    fixed_clusters = []
    clusters = list(clusters.clid2cluster.values())
    clusters.sort(key=lambda cl: cl.create_time)
    for cluster in clusters:
        if cluster.issue != issue_name:
            continue
        dt = ts_to_dt(cluster.create_time)
        date_str = dt.strftime(u"%B %d, %H:%M")
        fixed_clusters.append({
            "url": f"https://t.me/nyannews/{cluster.message.message_id}",
            "dt": date_str,
            "views": cluster.views,
            "sources_count": len([doc.channel_title for doc in cluster.docs]),
            "text": cluster.annotation_doc.patched_text
        })

    with open(prompt_path) as f:
        template = Template(f.read())

    prompt = template.render(clusters=fixed_clusters, batch_size=len(fixed_clusters)).strip() + "\n"
    print(prompt)

    messages = [{"role": "user", "content": prompt}]
    result = openai_completion(messages=messages, model_name=model_name)
    content = result.message.content.strip()
    print(content)

    poll = json.loads(content)
    print(poll)

    return poll


def main(
    mongo_config_path,
    client_config_path,
    renderer_config_path,
    duration_hours,
    issue_name,
    prompt_path,
    model_name,
):
    duration = int(duration_hours * 3600)
    clusters = Clusters.load_from_mongo(mongo_config_path, get_current_ts(), duration)
    client = TelegramClient(client_config_path)

    poll = make_poll(
        clusters,
        issue_name=issue_name,
        prompt_path=prompt_path,
        duration_hours=duration_hours,
        model_name=model_name,
    )
    if input("Post?y/n").strip() == "y":
        response = client.send_poll(question=poll["question"], options=poll["options"], issue_name=issue_name)
        assert "ok" in response.text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--renderer-config-path", type=str, required=True)
    parser.add_argument("--duration-hours", type=int, default=6)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, required=True)
    parser.add_argument("--model-name", type=str, default="gpt-4")
    args = parser.parse_args()
    main(**vars(args))
