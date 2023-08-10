import sys
import random

from tqdm import tqdm

from nyan.util import read_jsonl, write_jsonl


def shrink(obj):
    return {field: obj[field] for field in obj if field in save_fields}


input_path = sys.argv[1]
output_path = sys.argv[2]

docs = list(tqdm(read_jsonl(input_path)))
docs = [doc for doc in docs if doc["patched_text"] and doc["language"] == "ru"]
docs.sort(key=lambda x: x["pub_time"])
print(len(docs))

url2doc = {d["url"]: d for d in docs}
url2idx = {d["url"]: idx for idx, d in enumerate(docs)}
replies = [(r["reply_to"], r["url"]) for r in docs if "reply_to" in r]
print(len(replies))
existing_replies = [(url_from, url_to) for url_from, url_to in replies if url_from in url2doc and url_to in url2doc]
print(len(existing_replies))

save_fields = ("patched_text", "url", "pub_time", "language", "channel_id")

pairs = []
for url_from, url_to in existing_replies:
    anchor_doc = shrink(url2doc[url_to])
    anchor_idx = url2idx[url_to]

    positive_doc = shrink(url2doc[url_from])

    random_shift = random.randint(2, 20)
    negative_idx = anchor_idx - 1
    while negative_idx >= 0 and random_shift > 0:
        negative_doc = shrink(docs[negative_idx])
        if negative_doc["channel_id"] != anchor_doc["channel_id"]:
            negative_idx -= 1
            continue
        if negative_doc["url"] == positive_doc["url"]:
            negative_idx -= 1
            continue
        random_shift -= 1

    if negative_idx <= 0:
        continue
    pairs.append({
        "anchor": anchor_doc,
        "positive": positive_doc,
        "negative": negative_doc
    })

write_jsonl(output_path, pairs)
