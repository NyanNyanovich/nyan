import sys
import json
from collections import Counter

input_path = sys.argv[1]
output_path = sys.argv[2]

with open(input_path) as r, open(output_path, "w") as w:
    documents = [json.loads(line) for line in r]
    documents.sort(key=lambda x: x["pub_time"])
    used_urls = set()
    for doc in documents:
        if doc["url"] in used_urls:
            continue
        used_urls.add(doc["url"])
        w.write(json.dumps(doc, ensure_ascii=False).strip() + "\n")
