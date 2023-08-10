import sys
import json
from collections import Counter
from tqdm import tqdm

input_path = sys.argv[1]
output_path = sys.argv[2]

skip_idx = set()
with open(input_path) as r:
    records = []
    for idx, line in enumerate(tqdm(r)):
        record = json.loads(line)
        record = {k: v for k, v in record.items() if k in ("pub_time", "url")}
        record["idx"] = idx
        records.append(record)
    records.sort(key=lambda x: x["pub_time"])
    used_urls = set()
    for doc in tqdm(records):
        if doc["url"] in used_urls:
            skip_idx.add(doc["idx"])
            continue
        used_urls.add(doc["url"])
print("Found {} duplicates".format(len(skip_idx)))


with open(input_path) as r, open(output_path, "w") as w:
    for idx, line in enumerate(tqdm(r)):
        if idx in skip_idx:
            continue
        doc = json.loads(line)
        w.write(json.dumps(doc, ensure_ascii=False).strip() + "\n")
