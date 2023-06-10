import argparse
import random
import json
from datetime import datetime

from jinja2 import Template

from nyan.clusters import Clusters
from nyan.channels import Channels
from nyan.client import TelegramClient
from nyan.renderer import Renderer
from nyan.util import get_current_ts, ts_to_dt
from nyan.openai import openai_completion


FINAL_TEMPLATE = """
*Самое важное за {duration_hours} часов:*

{content}

_Сделано с помощью OpenAI GPT-4. Эксперимент. Сообщение совсем-совсем не достоверно._
"""


def summarize(clusters, issue_name, prompt_path, duration_hours, model_name):
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
            "sources": ", ".join([doc.channel_title for doc in cluster.docs]),
            "text": cluster.annotation_doc.patched_text
        })
    with open(prompt_path) as f:
        template = Template(f.read())
    prompt = template.render(clusters=fixed_clusters).strip() + "\n"
    print(prompt)

    messages = [{"role": "user", "content": prompt}]
    result = openai_completion(messages=messages, model_name=model_name)
    content = result.message.content.strip()
    print(content)
    titles = content[content.find("{"):content.rfind("}") + 1]
    titles = json.loads(titles)["titles"]
    titles = [r["emoji"] + " " + r["text"] for r in titles]

    final_content = FINAL_TEMPLATE.format(
        duration_hours=int(duration_hours),
        content="\n\n".join(titles)
    )
    return final_content


def main(
    channels_info_path,
    mongo_config_path,
    client_config_path,
    renderer_config_path,
    duration_hours,
    issue_name,
    prompt_path,
    model_name,
    auto
):
    duration = int(duration_hours * 3600)
    clusters = Clusters.load_from_mongo(mongo_config_path, get_current_ts(), duration)
    channels = Channels(channels_info_path)
    client = TelegramClient(client_config_path)

    summary_text = summarize(
        clusters,
        issue_name=issue_name,
        prompt_path=prompt_path,
        duration_hours=duration_hours,
        model_name=model_name
    )
    print(summary_text)

    should_publish = False
    if not auto:
        should_publish = input("Publish? y/n ").strip() == "y"

    if auto or should_publish:
        client.send_message(summary_text, issue_name=issue_name, parse_mode="Markdown")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channels-info-path", type=str, required=True)
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--renderer-config-path", type=str, required=True)
    parser.add_argument("--duration-hours", type=int, default=9)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, required=True)
    parser.add_argument("--model-name", type=str, default="gpt-4")
    parser.add_argument("--auto", default=False, action="store_true")
    args = parser.parse_args()
    main(**vars(args))
