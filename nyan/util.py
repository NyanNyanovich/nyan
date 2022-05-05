import os
import json
from datetime import datetime, timezone


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
