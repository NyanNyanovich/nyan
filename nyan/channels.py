import os
import json
from typing import Dict
from dataclasses import dataclass

from nyan.util import Serializable


@dataclass
class Channel(Serializable):
    name: int
    alias: str = ""
    groups: Dict[str, str] = None
    master: str = None
    disabled: bool = False
    emojis: Dict[str, str] = None
    colors: Dict[str, str] = None
    issue: str = None


class Channels:
    def __init__(self, path):
        self.channels = dict()

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
            channel.emojis = {issue: emojis[group] for issue, group in channel.groups.items()}
            channel.colors = {issue: colors[group] for issue, group in channel.groups.items()}
            self.add(channel)

    def add(self, channel):
        self.channels[channel.name] = channel

    def __getitem__(self, chid):
        return self.channels[chid]

    def __contains__(self, chid):
        return chid in self.channels

    def __iter__(self):
        return iter(self.channels.items())
