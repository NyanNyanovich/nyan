import argparse

from nyan.clusters import Clusters
from nyan.channels import Channels
from nyan.client import TelegramClient
from nyan.renderer import Renderer


def main(
    channels_info_path,
    posted_clusters_path,
    client_config_path,
    renderer_config_path,
    duration_days,
    issue_name
):
    clusters = Clusters.load(posted_clusters_path)
    channels = Channels(channels_info_path)
    client = TelegramClient(client_config_path)
    renderer = Renderer(renderer_config_path, channels)
    duration = duration_days * 24 * 3600

    ratings_text = renderer.render_ratings(clusters, channels, duration, issue_name)
    client.send_message(ratings_text, issue_name=issue_name)
    print(ratings_text)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channels-info-path", type=str, required=True)
    parser.add_argument("--posted-clusters-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, required=True)
    parser.add_argument("--renderer-config-path", type=str, required=True)
    parser.add_argument("--duration-days", type=int, required=True)
    parser.add_argument("--issue-name", type=str, default="main")
    args = parser.parse_args()
    main(**vars(args))
