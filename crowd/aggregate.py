import argparse
import os
from collections import defaultdict, Counter

import toloka.client as toloka
import pandas as pd
from nltk.metrics.agreement import AnnotationTask
from crowdkit.aggregation import DawidSkene

from nyan.util import write_jsonl, read_jsonl
from crowd.util import get_pool, read_token, read_pools_ids, get_key


def aggregate(
    records,
    res_field,
    key_fields,
    min_agreement=0.7,
    overlap=5
):
    records.sort(key=lambda x: x["assignment_id"])

    results = defaultdict(list)
    for r in records:
        if len(results[get_key(r, key_fields)]) >= overlap:
            continue
        results[get_key(r, key_fields)].append(r[res_field])

    data = {get_key(r, key_fields): r for r in records}

    votes, votes_distribution, res_distribution = dict(), Counter(), Counter()
    for key, res in results.items():
        res_count = Counter(res)
        overlap = len(res)
        res_win, votes_win = res_count.most_common(1)[0]
        res_distribution[res_win] += 1
        votes_part = float(votes_win) / overlap
        votes_distribution[votes_part] += 1
        votes[key] = votes_part
        data[key].update({
            res_field: res_win,
            "agreement": votes_part
        })

    total_samples = len(data)
    print("Total: ", total_samples)
    print("Aggreements:")
    sum_agreement = 0
    for v, sample_count in sorted(votes_distribution.items(), reverse=True):
        print("{}: {}".format(v, sample_count))
        sum_agreement += sample_count * v
    print("Average agreement:", sum_agreement / total_samples)
    print()

    print("Results:")
    for res, cnt in res_distribution.items():
        print("{}: {}".format(res, cnt))
    print()

    answers = [(r["worker_id"], get_key(r, key_fields), r[res_field]) for r in records]
    t = AnnotationTask(data=answers)
    print("Krippendorff’s alpha: {}".format(t.alpha()))

    answers = [
        (r["worker_id"], get_key(r, key_fields), r[res_field])
        for r in records if votes[get_key(r, key_fields)] >= min_agreement
    ]
    t = AnnotationTask(data=answers)
    print("Krippendorff’s alpha, border {}: {}".format(min_agreement, t.alpha()))
    print()

    data = {key: r for key, r in data.items()}
    data = list(data.values())
    for r in data:
        r.pop("worker_id")
        r.pop("assignment_id")
    data.sort(key=lambda x: x["agreement"], reverse=True)
    return data


def main(
    input_path,
    output_path,
    key_fields,
    res_field
):
    key_fields = key_fields.split(",")

    records = list(read_jsonl(input_path))
    agg_records = aggregate(records, res_field, key_fields)
    write_jsonl(output_path, agg_records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-fields", type=str, default="first_url,second_url")
    parser.add_argument("--res-field", type=str, default="result")
    parser.add_argument("--output-path", type=str, required=True)
    parser.add_argument("--input-path", type=str, required=True)
    args = parser.parse_args()
    main(**vars(args))
