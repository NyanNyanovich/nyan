import os
import json
from typing import Tuple
from time import sleep
from dataclasses import dataclass

from httpx import Timeout, Limits, HTTPTransport, Client

from nyan.util import Serializable


@dataclass
class IssueConfig:
    name: str
    channel_id: int
    discussion_id: int
    bot_token: str
    last_update_id: int = 0


@dataclass
class MessageId(Serializable):
    message_id: int
    issue: str = "main"
    from_discussion: bool = False

    def as_tuple(self):
        return (self.issue, self.message_id)

    def __hash__(self):
        return hash(self.as_tuple())

    def __eq__(self, another):
        return self.as_tuple() == another.self.as_tuple()


class TelegramClient:
    def __init__(self, config_path):
        assert os.path.exists(config_path)
        with open(config_path) as r:
            self.config = json.load(r)

        self.host = self.config.get("host", "https://api.telegram.org")
        timeout = Timeout(
            connect=self.config.get("connect_timeout", 30.0),
            read=self.config.get("read_timeout", 30.0),
            write=self.config.get("write_timeout", 30.0),
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

        self.issues = {config["name"]: IssueConfig(**config) for config in self.config["issues"]}
        self.discussions = {issue.name: dict() for _, issue in self.issues.items()}
        for issue_name in self.issues:
            self.update_discussion_mapping(issue_name)

    def send_message(
        self,
        text: str,
        issue_name: str,
        photos: Tuple[str] = tuple(),
        videos: Tuple[str] = tuple(),
        reply_to: int = None,
        parse_mode: str = "html"
    ) -> MessageId:
        if issue_name not in self.issues:
            print(f"Missing issue '{issue_name}' in client config")
            return None
        issue = self.issues[issue_name]
        response = None
        if len(photos) == 1:
            response = self._send_photo(text, photos[0], issue=issue, reply_to=reply_to)
        elif len(photos) > 1:
            response = self._send_photos(text, photos, issue=issue, reply_to=reply_to)
        elif len(videos) >= 1:
            response = self._send_video(text, videos[0], issue=issue, reply_to=reply_to)
        else:
            response = self._send_text(text, issue=issue, reply_to=reply_to, parse_mode=parse_mode)

        print("Send status code:", response.status_code)
        if response.status_code == 400 and "description" in response.text:
            response_dict = response.json()
            description = response_dict["description"]
            if description == "Bad Request: message caption is too long":
                response = self._send_text(text, issue=issue)
                print("Text only send status code:", response.status_code)

        if response.status_code != 200:
            print("Send error:", response.text)
            return None

        result = response.json()["result"]
        message_id = int(result["message_id"] if "message_id" in result else result[0]["message_id"])
        return MessageId(
            message_id=message_id,
            issue=issue_name,
            from_discussion=False
        )

    def send_poll(self, question, options, issue_name, reply_to: int = None):
        url_template = self.host + "/bot{}/sendPoll"
        issue = self.issues[issue_name]
        params = {
            "chat_id": issue.channel_id,
            "disable_notification": True,
            "question": question,
            "options": json.dumps(options)
        }
        if reply_to:
            params["reply_to_message_id"] = reply_to
            params["allow_sending_without_reply"] = True
        return self._post(url_template.format(issue.bot_token), params)

    def update_message(
        self,
        message: MessageId,
        text: str,
        is_caption: bool
    ):
        assert not message.from_discussion
        issue = self.issues[message.issue]
        message_id = message.message_id
        if not is_caption:
            response = self._edit_text(message_id, text, issue=issue)
        else:
            response = self._edit_caption(message_id, text, issue=issue)
        print("Update status code:", response.status_code)
        if response.status_code != 200:
            print("Update error:", response.text)

    def update_discussion_mapping(self, issue_name: str):
        if issue_name not in self.issues:
            print(f"Missing issue '{issue_name}' in client config")
            return None
        issue = self.issues[issue_name]
        updates = self._get_updates(issue)
        if not updates:
            return dict()
        for update in updates:
            if "message" not in update:
                continue
            message = update["message"]
            if "forward_from_chat" not in message:
                continue
            if issue.channel_id != message["forward_from_chat"]["id"]:
                continue
            if issue.discussion_id != message["chat"]["id"]:
                continue
            orig_message_id = message["forward_from_message_id"]
            discussion_message_id = message["message_id"]
            self.discussions[issue.name][orig_message_id] = discussion_message_id

    def get_discussion(self, message: str):
        discussion_message_id = self.discussions[message.issue].get(message.message_id, None)
        return MessageId(
            message_id=discussion_message_id,
            issue=message.issue,
            from_discussion=True
        )

    def send_discussion_message(self, text, discussion_message):
        assert discussion_message.from_discussion
        issue = self.issues[discussion_message.issue]
        if not issue.discussion_id or not discussion_message.message_id:
            return None
        url_template = self.host + "/bot{}/sendMessage"
        params = {
            "chat_id": issue.discussion_id,
            "text": text,
            "parse_mode": "html",
            "disable_web_page_preview": False,
            "reply_to_message_id": discussion_message.message_id
        }
        return self._post(url_template.format(issue.bot_token), params)

    def _send_text(self, text, issue, reply_to: int = None, parse_mode: str = "html"):
        url_template = self.host + "/bot{}/sendMessage"
        params = {
            "chat_id": issue.channel_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
            "disable_notification": True
        }
        if reply_to:
            params["reply_to_message_id"] = reply_to
            params["allow_sending_without_reply"] = True
        return self._post(url_template.format(issue.bot_token), params)

    def _send_photo(self, text, photo, issue, reply_to: int = None):
        url_template = self.host + "/bot{}/sendPhoto"
        params = {
            "chat_id": issue.channel_id,
            "caption": text,
            "photo": photo,
            "parse_mode": "html",
            "disable_notification": True
        }
        if reply_to:
            params["reply_to_message_id"] = reply_to
            params["allow_sending_without_reply"] = True
        return self._post(url_template.format(issue.bot_token), params)

    def _send_video(self, text, video, issue, reply_to: int = None):
        url_template = self.host + "/bot{}/sendVideo"
        params = {
            "chat_id": issue.channel_id,
            "caption": text,
            "video": video,
            "parse_mode": "html",
            "disable_notification": True
        }
        if reply_to:
            params["reply_to_message_id"] = reply_to
            params["allow_sending_without_reply"] = True
        return self._post(url_template.format(issue.bot_token), params)

    def _send_photos(self, text, photos, issue, reply_to: int = None):
        url_template = self.host + "/bot{}/sendMediaGroup"
        media = [{
            "type": "photo",
            "media": photo,
            "caption": text if i == 0 else "",
            "parse_mode": "html"
        } for i, photo in enumerate(photos)]
        params = {
            "chat_id": issue.channel_id,
            "disable_notification": True,
            "media": json.dumps(media)
        }
        if reply_to:
            params["reply_to_message_id"] = reply_to
            params["allow_sending_without_reply"] = True
        return self._post(url_template.format(issue.bot_token), params)

    def _edit_text(self, message_id, text, issue):
        url_template = self.host + "/bot{}/editMessageText"
        params = {
            "chat_id": issue.channel_id,
            "text": text,
            "parse_mode": "html",
            "disable_web_page_preview": True,
            "message_id": message_id
        }
        return self._post(url_template.format(issue.bot_token), params)

    def _edit_caption(self, message_id, text, issue):
        url_template = self.host + "/bot{}/editMessageCaption"
        params = {
            "chat_id": issue.channel_id,
            "message_id": message_id,
            "caption": text,
            "parse_mode": "html",
        }
        return self._post(url_template.format(issue.bot_token), params)

    def _get_updates(self, issue):
        url_template = self.host + "/bot{}/getUpdates"
        params = {
            "timeout": 10
        }
        if issue.last_update_id != 0:
            params["offset"] = issue.last_update_id
        response = self.client.get(url_template.format(issue.bot_token), params=params, timeout=20)
        if response.status_code != 200:
            return None
        updates = response.json()["result"]
        for update in updates:
            issue.last_update_id = max(issue.last_update_id, update["update_id"]) + 1
        return updates

    def _post(self, url, params):
        return self.client.post(url, data=params)
