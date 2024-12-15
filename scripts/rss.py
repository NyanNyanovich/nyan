import argparse
import mimetypes

from nyan.clusters import Clusters
from nyan.util import get_current_ts, ts_to_dt
from nyan.channels import Channels
from nyan.renderer import Renderer

from feedgen.feed import FeedGenerator
from ghp_import import ghp_import


DESCRIPTION = """НЯН. Умный агрегатор новостных каналов в Телеграме.
Автоматически выбирает важное и присылает одним сообщением со ссылками на все источники."""


def create_feed():
    feed = FeedGenerator()
    feed.id("nyannews")
    feed.title("НЯН - Агрегатор новостей – Telegram")
    feed.author({"name": "Nyan Nyanovich", "email": "nyan_news@protonmail.com"})
    feed.link(href="https://t.me/nyannews")
    feed.description(DESCRIPTION)
    feed.logo("https://nyannyanovich.github.io/nyan/logo.jpg")
    feed.language("ru")
    return feed


def add_cluster(feed, cluster, renderer, issue_name):
    entry = feed.add_entry()
    entry.id(str(cluster.clid))
    entry.title(cluster.cropped_title)
    text = renderer.render_cluster(cluster, issue_name)
    text = text.replace("\n", "</br>")
    entry.description(text)
    entry.link(href=cluster.get_url("https://t.me/nyannews", "main"))
    entry.published(ts_to_dt(cluster.create_time))
    if cluster.images:
        photo = cluster.images[0]
        mimetype = mimetypes.guess_type(photo)[0]
        entry.enclosure(url=photo, type=mimetype)
    if cluster.videos:
        video = cluster.videos[0]
        mimetype = mimetypes.guess_type(video.split("?")[0])[0]
        entry.enclosure(url=video, type=mimetype)
    return entry


def main(
    output_path,
    mongo_config,
    channels_config,
    renderer_config,
    duration_hours,
    issue_name
):
    duration = int(duration_hours * 3600)
    clusters = Clusters.load_from_mongo(mongo_config, get_current_ts(), duration)
    clusters = list(clusters.clid2cluster.values())
    fixed_clusters = []
    for cluster in clusters:
        messages = [m for m in cluster.messages if m.issue == issue_name]
        if not messages:
            continue
        fixed_clusters.append(cluster)
    clusters = fixed_clusters
    clusters.sort(key=lambda cl: cl.create_time, reverse=True)

    channels = Channels(channels_config)
    renderer = Renderer(renderer_config, channels)

    feed = create_feed()
    for cluster in clusters:
        add_cluster(feed, cluster, renderer, issue_name)

    feed.rss_file(output_path)
    ghp_import("static", push=True, no_history=True, mesg="Update RSS", branch="static")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, default="static/rss_feed.xml")
    parser.add_argument("--mongo-config", type=str, default="configs/mongo_config.json")
    parser.add_argument("--renderer-config", type=str, default="configs/renderer_config.json")
    parser.add_argument("--channels-config", type=str, default="channels.json")
    parser.add_argument("--duration-hours", type=int, default=24)
    parser.add_argument("--issue-name", type=str, default="main")
    args = parser.parse_args()
    main(**vars(args))
