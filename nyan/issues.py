import os
import json
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class IssueConfig:
    name: str
    channel_id: int
    discussion_id: int
    bot_token: str
    last_update_id: int = 0
    style_name: Optional[str] = None


class IssueConfigs:
    def __init__(self, config_path: str) -> None:
        assert os.path.exists(config_path)
        with open(config_path) as r:
            self.config = json.load(r)
        self.issues: Dict[str, IssueConfig] = {
            config["name"]: IssueConfig(**config) for config in self.config["issues"]
        }

    def get_issues(self) -> Dict[str, IssueConfig]:
        return list(self.issues)
