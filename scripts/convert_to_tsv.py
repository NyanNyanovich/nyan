import csv
import sys
from nyan.util import read_jsonl

input_path = sys.argv[1]
output_path = sys.argv[2]
docs_path = sys.argv[3]

records = read_jsonl(input_path)
docs = {doc["url"]: doc for doc in read_jsonl(docs_path)}
with open(output_path, "w") as w:
    writer = csv.writer(w, delimiter="\t")
    mapping = {
        "url1": "INPUT:first_url",
        "first_url": "INPUT:first_url",
        "url2": "INPUT:second_url",
        "second_url": "INPUT:second_url",
        "result": "GOLDEN:result"
    }
    header = [
        "INPUT:first_url",
        "INPUT:second_url",
        "INPUT:first_text",
        "INPUT:second_text",
        "GOLDEN:result"
    ]
    writer.writerow(header)
    for record in records:
        if record["result"] == "trash":
            continue
        for key, value in mapping.items():
            if key in record:
                record[value] = record.pop(key)
        first_doc = docs[record["INPUT:first_url"]]
        second_doc = docs[record["INPUT:second_url"]]
        record["INPUT:first_text"] = " ".join(first_doc["patched_text"].split())
        record["INPUT:second_text"] = " ".join(second_doc["patched_text"].split())
        writer.writerow([record[key] for key in header])
