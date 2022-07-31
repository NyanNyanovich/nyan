import os
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, fields


def read_jsonl(file_path):
    assert os.path.exists(file_path)
    with open(file_path) as r:
        for line in r:
            yield json.loads(line)


def write_jsonl(file_path, records):
    with open(file_path, "w") as w:
        for record in records:
            w.write(json.dumps(record, ensure_ascii=False).strip() + "\n")


def get_current_ts():
    return int(datetime.now().replace(tzinfo=timezone.utc).timestamp())


def ts_to_dt(timestamp, offset=3):
    dt = datetime.fromtimestamp(timestamp + offset * 3600)
    return dt.strftime("%d-%m-%y %H:%M")


@dataclass
class Serializable:
    not_serializing = tuple()

    @classmethod
    def fromdict(cls, d):
        if d is None:
            return None
        keys = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in keys}
        return cls(**d)

    def asdict(self):
        d = asdict(self)
        for field in self.not_serializing:
            d.pop(field, None)
        d.pop("not_serializing", None)
        return d

    @classmethod
    def deserialize(cls, line):
        return cls.fromdict(json.loads(line))

    def serialize(self):
        return json.dumps(self.asdict(), ensure_ascii=False)
