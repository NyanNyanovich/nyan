import os
import json
from time import sleep

import requests
from httpx import Timeout, Limits, HTTPTransport, Client


class TelegramClient:
    def __init__(self, config_path):
        assert os.path.exists(config_path)
        with open(config_path) as r:
            self.config = json.load(r)

        timeout = Timeout(
            connect=self.config.get("connect_timeout", 5.0),
            read=self.config.get("read_timeout", 5.0),
            write=self.config.get("write_timeout", 5.0),
            pool=self.config.get("pool_timeout", 1.0),
        )
        limits = Limits(
            max_connections=self.config.get("connection_pool_size", 1),
            max_keepalive_connections=self.config.get("connection_pool_size", 1),
        )
        transport = HTTPTransport(
            retries=self.config.get("retries", 5)
        )
        self.client = Client(
            timeout=timeout,
            limits=limits,
            transport=transport
        )

        self.channel_id = self.config["channel_id"]
        self.discussion_id = self.config["discussion_id"]
        self.bot_token = self.config["bot_token"]
        self.discussions = dict()
        self.last_update_id = 0
        self.update_discussion_mapping()

    def send_message(self, text, photos=tuple(), videos=tuple()):
        if len(photos) == 1:
            return self.send_photo(text, photos[0])
        elif len(photos) > 1:
            return self.send_photos(text, photos)
        elif len(videos) >= 1:
            return self.send_video(text, videos[0])
        return self.send_text(text)

    def update_message(self, message_id, text, is_caption):
        if not is_caption:
            return self.edit_text(message_id, text)
        return self.edit_caption(message_id, text)

    def send_text(self, text):
        url_template = "https://api.telegram.org/bot{}/sendMessage"
        params = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "html",
            "disable_web_page_preview": True,
            "disable_notification": True
        }
        return self.post(url_template.format(self.bot_token), params)

    def send_photo(self, text, photo):
        url_template = "https://api.telegram.org/bot{}/sendPhoto"
        params = {
            "chat_id": self.channel_id,
            "caption": text,
            "photo": photo,
            "parse_mode": "html",
            "disable_notification": True
        }
        return self.post(url_template.format(self.bot_token), params)

    def send_video(self, text, video):
        url_template = "https://api.telegram.org/bot{}/sendVideo"
        params = {
            "chat_id": self.channel_id,
            "caption": text,
            "video": video,
            "parse_mode": "html",
            "disable_notification": True
        }
        return self.post(url_template.format(self.bot_token), params)

    def send_photos(self, text, photos):
        url_template = "https://api.telegram.org/bot{}/sendMediaGroup"
        media = [{
            "type": "photo",
            "media": photo,
            "caption": text if i == 0 else "",
            "parse_mode": "html"
        } for i, photo in enumerate(photos)]
        params = {
            "chat_id": self.channel_id,
            "disable_notification": True,
            "media": json.dumps(media)
        }
        return self.post(url_template.format(self.bot_token), params)

    def edit_text(self, message_id, text):
        url_template = "https://api.telegram.org/bot{}/editMessageText"
        params = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "html",
            "disable_web_page_preview": True,
            "message_id": message_id
        }
        return self.post(url_template.format(self.bot_token), params)

    def edit_caption(self, message_id, text):
        url_template = "https://api.telegram.org/bot{}/editMessageCaption"
        params = {
            "chat_id": self.channel_id,
            "message_id": message_id,
            "caption": text,
            "parse_mode": "html",
        }
        return self.post(url_template.format(self.bot_token), params)

    def send_discussion_message(self, text, reply_to_message_id):
        if not self.discussion_id or not reply_to_message_id:
            return None
        url_template = "https://api.telegram.org/bot{}/sendMessage"
        params = {
            "chat_id": self.discussion_id,
            "text": text,
            "parse_mode": "html",
            "disable_web_page_preview": False,
            "reply_to_message_id": reply_to_message_id
        }
        return self.post(url_template.format(self.bot_token), params)

    def get_updates(self):
        url_template = "https://api.telegram.org/bot{}/getUpdates"
        params = {
            "timeout": 10
        }
        if self.last_update_id != 0:
            params["offset"] = self.last_update_id
        response = self.client.get(url_template.format(self.bot_token), params=params, timeout=20)
        if response.status_code != 200:
            return None
        updates = response.json()["result"]
        for update in updates:
            self.last_update_id = max(self.last_update_id, update["update_id"]) + 1
        return updates

    def update_discussion_mapping(self):
        updates = self.get_updates()
        if not updates:
            return dict()
        for update in updates:
            if "message" not in update:
                continue
            message = update["message"]
            if "forward_from_chat" not in message:
                continue
            if self.channel_id != message["forward_from_chat"]["id"]:
                continue
            if self.discussion_id != message["chat"]["id"]:
                continue
            orig_message_id = message["forward_from_message_id"]
            discussion_message_id = message["message_id"]
            self.discussions[orig_message_id] = discussion_message_id

    def get_discussion(self, message_id):
        return self.discussions.get(message_id, None)

    def post(self, url, params):
        return self.client.post(url, data=params)
