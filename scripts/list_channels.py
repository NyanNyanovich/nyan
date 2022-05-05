import argparse
from collections import defaultdict

from nyan.channels import Channels
from nyan.client import TelegramClient


def list_channels(client_config_path, channels_path):
    client = TelegramClient(client_config_path)
    channels = Channels.load(channels_path)

    groups = defaultdict(list)
    for _, ch in channels:
        groups[ch.group].append(ch)

    text = ""
    for group_name, group in groups.items():
        emoji = group[0].emoji
        text += emoji
        for i, ch in enumerate(group):
            text += '<a href="https://t.me/{}">{}</a> • '.format(ch.id, ch.alias)
        text += "\n\n"
    print(text)
    client.send_message(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channels-path", type=str, required=True)
    parser.add_argument("--client-config-path", type=str, default="configs/client_config.json")
    args = parser.parse_args()
    list_channels(**vars(args))
