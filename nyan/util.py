import os
import json
import random
from typing import TypeVar, List, Any, Iterable, Dict, Type
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, fields

import numpy as np
import torch


def read_jsonl(file_path: str, sample_rate: float = 1.0) -> Iterable[Dict[str, Any]]:
    assert os.path.exists(file_path)
    with open(file_path) as r:
        for line in r:
            if not line:
                continue
            if random.random() > sample_rate:
                continue
            yield json.loads(line)


def write_jsonl(file_path: str, records: List[Dict[str, Any]]) -> None:
    with open(file_path, "w") as w:
        for record in records:
            w.write(json.dumps(record, ensure_ascii=False).strip() + "\n")


def get_current_ts() -> int:
    return int(datetime.now().replace(tzinfo=timezone.utc).timestamp())


def ts_to_dt(timestamp: int, offset: int = 3) -> datetime:
    return datetime.fromtimestamp(timestamp, timezone(timedelta(hours=offset)))


T = TypeVar("T", bound="Serializable")


@dataclass
class Serializable:
    @classmethod
    def fromdict(cls: Type[T], d: Dict[str, Any]) -> T:
        if d is None:
            return None
        keys = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in keys}
        return cls(**d)

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def deserialize(cls: Type[T], line: str) -> T:
        return cls.fromdict(json.loads(line))

    def serialize(self) -> str:
        return json.dumps(self.asdict(), ensure_ascii=False)


def set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:2"
    os.environ["PL_GLOBAL_SEED"] = str(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def gen_batch(records: List[Any], batch_size: int) -> Iterable[List[Any]]:
    batch_start = 0
    while batch_start < len(records):
        batch_end = batch_start + batch_size
        batch = records[batch_start:batch_end]
        batch_start = batch_end
        yield batch
