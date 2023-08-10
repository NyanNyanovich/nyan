import argparse
import random
import json

from scipy.spatial.distance import cosine
from annoy import AnnoyIndex

from nyan.util import write_jsonl, read_jsonl


def main(
    documents_path,
    existing_path,
    output_path,
    seed,
    nrows
):
    random.seed(seed)
    docs = list(read_jsonl(documents_path))
    docs = [doc for doc in docs if doc["language"] == "ru" and doc["category"] != "not_news"]

    existing_records = {(r["first_url"], r["second_url"]) for r in read_jsonl(existing_path)}
    existing_records |= {(r["second_url"], r["first_url"]) for r in read_jsonl(existing_path)}

    embedding_dim = len(docs[0]["embedding"])
    ann_index = AnnoyIndex(embedding_dim, "angular")
    for i, doc in enumerate(docs):
        ann_index.add_item(i, doc["embedding"])
    ann_index.build(100)

    records = []
    while len(records) < nrows:
        first_doc_index = random.randint(0, len(docs))
        first_doc = docs[first_doc_index]
        neighbors, distances = ann_index.get_nns_by_item(first_doc_index, 20, include_distances=True)

        indices = [i for distance, i in sorted(zip(distances, neighbors))][3:]
        if not indices:
            continue

        indices = [i for i in indices if abs(docs[i]["pub_time"] - first_doc["pub_time"]) < 3600 * 6]
        if not indices:
            continue

        second_doc_index = random.choice(indices)
        second_doc = docs[second_doc_index]
        if (first_doc["url"], second_doc["url"]) in existing_records:
            continue
        if (second_doc["url"], first_doc["url"]) in existing_records:
            continue
        records.append({
            "first_url": first_doc["url"],
            "second_url": second_doc["url"],
            "first_text": " ".join(first_doc["patched_text"].split()),
            "second_text": " ".join(second_doc["patched_text"].split()),
            "distance": cosine(second_doc["embedding"], first_doc["embedding"])
        })
        existing_records.add((first_doc["url"], second_doc["url"]))
    write_jsonl(output_path, records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, default="data/sample.jsonl")
    parser.add_argument("--documents-path", type=str, required=True)
    parser.add_argument("--existing-path", type=str, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--nrows", type=int, default=180)
    args = parser.parse_args()
    main(**vars(args))
