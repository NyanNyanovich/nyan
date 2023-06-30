import argparse
import random
import json
from datetime import datetime

from jinja2 import Template

from nyan.clusters import Clusters
from nyan.client import TelegramClient
from nyan.renderer import Renderer
from nyan.util import get_current_ts, ts_to_dt, gen_batch
from nyan.openai import openai_completion


FINAL_TEMPLATE = """
*Самое важное за {duration_hours} часов:*

{content}

_Сделано с помощью OpenAI GPT-4. Сообщение совсем не достоверно. Правдивость информации не проверяется._
"""


def summarize(
    clusters,
    issue_name,
    prompt_path,
    duration_hours,
    model_name,
    news_batch_size
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

    all_titles = []
    for batch in gen_batch(fixed_clusters, news_batch_size):
        prompt = template.render(clusters=batch, batch_size=len(batch)).strip() + "\n"
        print(prompt)

        messages = [{"role": "user", "content": prompt}]
        result = openai_completion(messages=messages, model_name=model_name)
        content = result.message.content.strip()
        print(content)

        titles = content[content.find("{"):content.rfind("}") + 1]
        titles = json.loads(titles)["titles"]
        if len(batch) > 1:
            max_importance = max([int(t["importance"]) for t in titles])
            for title in titles:
                title["importance"] = (title["importance"] - 1.0) / (max_importance - 1.0)
        all_titles.extend(titles)

    titles = all_titles
    titles.sort(key=lambda r: r["importance"], reverse=True)
    titles = [t for t in titles if not t["is_duplicate"]]
    titles = titles[:5]

    final_titles = []
    for r in titles:
        link = "[{}]({})".format(r["verb"], r["url"])
        fixed_title = r["title"].replace(r["verb"], link)
        if fixed_title == r["title"]:
            link = "[{}]({})".format(r["verb"].capitalize(), r["url"])
            fixed_title = fixed_title.replace(r["verb"].capitalize(), link)
        final_titles.append(r["emoji"] + " " + fixed_title)

    return FINAL_TEMPLATE.format(
        duration_hours=int(duration_hours),
        content="\n\n".join(final_titles)
    )


def main(
    mongo_config_path,
    client_config_path,
    renderer_config_path,
    duration_hours,
    news_batch_size,
    issue_name,
    prompt_path,
    model_name,
    auto
):
    duration = int(duration_hours * 3600)
    clusters = Clusters.load_from_mongo(mongo_config_path, get_current_ts(), duration)
    client = TelegramClient(client_config_path)

    summary_text = summarize(
        clusters,
        issue_name=issue_name,
        prompt_path=prompt_path,
        duration_hours=duration_hours,
        model_name=model_name,
        news_batch_size=news_batch_size
    )
    print(summary_text)

    should_publish = False
    if not auto:
        should_publish = input("Publish? y/n ").strip() == "y"

    if auto or should_publish:
        client.send_message(summary_text, issue_name=issue_name, parse_mode="Markdown")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-config-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--renderer-config-path", type=str, required=True)
    parser.add_argument("--duration-hours", type=int, default=12)
    parser.add_argument("--news-batch-size", type=int, default=16)
    parser.add_argument("--issue-name", type=str, default="main")
    parser.add_argument("--prompt-path", type=str, required=True)
    parser.add_argument("--model-name", type=str, default="gpt-4")
    parser.add_argument("--auto", default=False, action="store_true")
    args = parser.parse_args()
    main(**vars(args))
