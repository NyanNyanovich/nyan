import sys
import json
from collections import Counter

from tqdm import tqdm

input_path = sys.argv[1]
output_path = sys.argv[2]
docs_path = sys.argv[3]

with open(input_path) as r, open(output_path, "w") as w, open(docs_path, "r") as df:
    docs = [json.loads(line) for line in df]
    url2doc = {doc["url"]: doc for doc in docs}
    clusters = [json.loads(line) for line in r]
    clusters.sort(key=lambda x: min([doc["pub_time"] for doc in x["docs"]]))
    for cluster in tqdm(clusters):
        fixed_docs = []
        for doc in cluster["docs"]:
            new_doc = url2doc.get(doc["url"])
            if not new_doc:
                continue
            fixed_docs.append(doc["url"])
        cluster["docs"] = fixed_docs

        annot_doc = cluster["annotation_doc"]
        if annot_doc["url"] not in url2doc:
            continue
        cluster["annotation_doc"] = annot_doc["url"]

        first_doc = cluster["first_doc"]
        if first_doc["url"] not in url2doc:
            continue
        cluster["first_doc"] = first_doc["url"]

        w.write(json.dumps(cluster, ensure_ascii=False).strip() + "\n")
