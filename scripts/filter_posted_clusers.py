import sys
import json
from collections import Counter

input_path = sys.argv[1]
output_path = sys.argv[2]
docs_path = sys.argv[3]

with open(input_path) as r, open(output_path, "w") as w, open(docs_path, "r") as df:
    urls = {json.loads(line)["url"] for line in df}
    seen = set()
    for line in r:
        cluster = json.loads(line)
        if isinstance(cluster["annotation_doc"], str):
            url = cluster["annotation_doc"]
            if url not in urls:
                continue
            url = cluster["first_doc"]
            if url not in urls:
                continue
            cluster["docs"] = [url for url in cluster["docs"] if url in urls]
        else:
            annot_doc = cluster["annotation_doc"]
            if annot_doc["url"] not in urls:
                continue
            cluster["annotation_doc"] = annot_doc["url"]

            first_doc = cluster["first_doc"]
            if first_doc["url"] not in urls:
                continue
            cluster["first_doc"] = first_doc["url"]

            fixed_docs = [doc["url"] for doc in cluster["docs"] if doc["url"] in urls]
            cluster["docs"] = fixed_docs

        url = cluster["annotation_doc"]
        if url in seen:
            continue
        seen.add(url)
        w.write(json.dumps(cluster, ensure_ascii=False).strip() + "\n")
