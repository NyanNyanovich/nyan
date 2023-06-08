import argparse

from jinja2 import Template

from nyan.clusters import Clusters
from nyan.channels import Channels
from nyan.client import TelegramClient
from nyan.renderer import Renderer
from nyan.util import get_current_ts, ts_to_dt
from nyan.openai import openai_completion


def summarize(clusters, issue_name, prompt_path):
    fixed_clusters = []
    for cluster in clusters.clid2cluster.values():
        if cluster.issue != issue_name:
            continue
        fixed_clusters.append({
            "url": f"https://t.me/nyannews/{cluster.message.message_id}",
            "dt":  ts_to_dt(cluster.annotation_doc.pub_time),
            "views": cluster.views,
            "source": cluster.annotation_doc.channel_title,
            "text": cluster.annotation_doc.patched_text
        })
    with open(prompt_path) as f:
        template = Template(f.read())
    prompt = template.render(clusters=fixed_clusters).strip() + "\n"
    print(prompt)

    messages = [{"role": "user", "content": prompt}]
    result = openai_completion(messages=messages)
    content = result.message.content.strip()
    final_content = "Самое важное за 12 часов:\n\n" + content + "\n\n_Сделано с помощью OpenAI API. Экспериментальная функциональность._"
    return final_content


def main(
    channels_info_path,
    mongo_config_path,
    client_config_path,
    renderer_config_path,
    duration_days,
    issue_name,
    prompt_path
):
    duration = int(duration_days * 24 * 3600)
    clusters = Clusters.load_from_mongo(mongo_config_path, get_current_ts(), duration)
    channels = Channels(channels_info_path)
    client = TelegramClient(client_config_path)

    summary_text = summarize(clusters, issue_name, prompt_path)
    print(summary_text)

    client.send_message(summary_text, issue_name=issue_name, parse_mode="Markdown")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channels-info-path", type=str, required=True)
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--renderer-config-path", type=str, required=True)
    parser.add_argument("--duration-days", type=float, required=True)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, required=True)
    args = parser.parse_args()
    main(**vars(args))
