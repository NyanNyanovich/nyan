import json
from typing import Dict, Optional, Iterator, Tuple
from dataclasses import dataclass

from nyan.util import Serializable


@dataclass
class Channel(Serializable):
    name: str
    groups: Dict[str, str]
    alias: str = ""
    master: Optional[str] = None
    disabled: bool = False
    emojis: Optional[Dict[str, str]] = None
    colors: Optional[Dict[str, str]] = None
    issue: Optional[str] = None


def normalize_channel_id(chid: str) -> str:
    return chid.strip().lower()


class Channels:
    def __init__(self, path: str) -> None:
        self.channels: Dict[str, Channel] = dict()

        with open(path) as r:
            config = json.load(r)
        emojis = config["emojis"]
        colors = config["colors"]
        self.emojis: Dict[str, str] = emojis
        self.colors: Dict[str, str] = colors
        default_groups = config["default_groups"]
        for channel in config["channels"]:
            channel = Channel.fromdict(channel)
            assert channel.groups
            assert channel.issue
            for issue, group in default_groups.items():
                if issue not in channel.groups:
                    channel.groups[issue] = group
            channel.emojis = {
                issue: emojis[group] for issue, group in channel.groups.items()
            }
            channel.colors = {
                issue: colors[group] for issue, group in channel.groups.items()
            }
            self.add(channel)

    def add(self, channel: Channel) -> None:
        chid = normalize_channel_id(channel.name)
        assert chid not in self.channels, "Duplicate channel: {}".format(channel.name)
        self.channels[chid] = channel

    def __getitem__(self, chid: str) -> Channel:
        return self.channels[normalize_channel_id(chid)]

    def __contains__(self, chid: str) -> bool:
        return normalize_channel_id(chid) in self.channels

    def __iter__(self) -> Iterator[Tuple[str, Channel]]:
        return iter(self.channels.items())
