import os
import json
from dataclasses import dataclass, asdict, fields


@dataclass
class Channel:
    name: int
    alias: str = ""
    group: str = "purple"

    @classmethod
    def fromdict(cls, d):
        if d is None:
            return None
        keys = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in keys}
        return cls(**d)

    def asdict(self):
        return asdict(self)

    @property
    def emoji(self):
        if self.group == "red":
            return "\U0001F1F7\U0001F1FA"  # Russian flag
        elif self.group == "blue":
            return "\U0001F30E"  # globe
        elif self.group == "purple":
            return "\U00002696\U0000FE0F"  # balance scale
        return ""


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
