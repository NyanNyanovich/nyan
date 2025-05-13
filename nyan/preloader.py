import argparse
from typing import Optional

from nyan.daemon import Daemon


def main(
    input_path: Optional[str],
    posted_clusters_path: Optional[str],
    client_config_path: str,
    annotator_config_path: str,
    clusterer_config_path: str,
    ranker_config_path: str,
    channels_info_path: str,
    renderer_config_path: str,
    mongo_config_path: Optional[str],
    daemon_config_path: str,
) -> None:
    daemon = Daemon(
        client_config_path=client_config_path,
        annotator_config_path=annotator_config_path,
        clusterer_config_path=clusterer_config_path,
        ranker_config_path=ranker_config_path,
        channels_info_path=channels_info_path,
        renderer_config_path=renderer_config_path,
        daemon_config_path=daemon_config_path,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", type=str, default=None)
    parser.add_argument("--mongo-config-path", type=str, default=None)
    parser.add_argument("--posted-clusters-path", type=str, default=None)
    parser.add_argument("--channels-info-path", type=str, default="channels.json")
    parser.add_argument(
        "--client-config-path", type=str, default="configs/client_config.json"
    )
    parser.add_argument(
        "--annotator-config-path", type=str, default="configs/annotator_config.json"
    )
    parser.add_argument(
        "--clusterer-config-path", type=str, default="configs/clusterer_config.json"
    )
    parser.add_argument(
        "--renderer-config-path", type=str, default="configs/renderer_config.json"
    )
    parser.add_argument(
        "--ranker-config-path", type=str, default="configs/ranker_config.json"
    )
    parser.add_argument(
        "--daemon-config-path", type=str, default="configs/daemon_config.json"
    )
    args = parser.parse_args()
    main(**vars(args))
