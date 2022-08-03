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
    issue: str = None


class Channels:
    def __init__(self):
        self.channels = dict()

    def add(self, channel):
        self.channels[channel.name] = channel

    def __getitem__(self, chid):
        return self.channels[chid]

    def __contains__(self, chid):
        return chid in self.channels

    def __iter__(self):
        return iter(self.channels.items())

    @classmethod
    def load(self, path):
        assert os.path.exists(path)
        channels = Channels()
        with open(path) as r:
            config = json.load(r)
            emojis = config["emojis"]
            for channel in config["channels"]:
                channel = Channel.fromdict(channel)
                channel.emojis = {issue: emojis[group] for issue, group in channel.groups.items()}
                channels.add(channel)
        return channels
