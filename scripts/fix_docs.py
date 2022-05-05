import sys

from nyan.util import read_jsonl, write_jsonl

input_path = sys.argv[1]
output_path = sys.argv[2]

docs = read_jsonl(input_path)
fixed_docs = []
for doc in docs:
    doc.pop("embedding")
    doc.pop("category")
    if doc["pub_time"] < 1649116800 + 6 * 3600:
        continue
    fixed_docs.append(doc)
fixed_docs.sort(key=lambda x: x["pub_time"])
write_jsonl(output_path, fixed_docs)
