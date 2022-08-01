import os
import json
from dataclasses import dataclass

from nyan.util import Serializable


@dataclass
class Channel(Serializable):
    name: int
    alias: str = ""
    group: str = "purple"
    master: str = None
    disabled: bool = False

    @property
    def emoji(self):
        emojis = {
            "red": "\U0001F1F7\U0001F1FA",  # Russian flag
            "blue": "\U0001F30E",  # Globe
            "purple": "\U00002696\U0000FE0F",  # Balance scale
            "tech": "\U0001f4bb",  # Laptop
        }
        return emojis.get(self.group, "")

    @property
    def issue(self):
        issues = {
            "red": "main",
            "blue": "main",
            "purple": "main",
            "tech": "tech"
        }
        assert self.group in issues, 'Unknown group "{self.group}", update issues dictionary!'
        return issues[self.group]


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
            for channel in json.load(r):
                channels.add(Channel.fromdict(channel))
        return channels
