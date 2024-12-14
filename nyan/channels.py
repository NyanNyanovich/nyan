import os
import json
from typing import Dict, Optional, Iterable, Tuple
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


class Channels:
    def __init__(self, path: str) -> None:
        self.channels: Dict[str, Channel] = dict()

        with open(path) as r:
            config = json.load(r)
        emojis = config["emojis"]
        colors = config["colors"]
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
        self.channels[channel.name] = channel

    def __getitem__(self, chid: str) -> Channel:
        return self.channels[chid]

    def __contains__(self, chid: str) -> bool:
        return chid in self.channels

    def __iter__(self) -> Iterable[Tuple[str, Channel]]:
        return iter(self.channels.items())
