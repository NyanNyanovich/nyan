import argparse
import os
from collections import defaultdict, Counter

import toloka.client as toloka

from nyan.util import write_jsonl
from crowd.util import get_pool, read_token, read_pools_ids


def main(
    token_path,
    output_path,
    pools_path,
    input_fields,
    res_field
):
    input_fields = input_fields.split(",")
    toloka_token = read_token(token_path)
    toloka_client = toloka.TolokaClient(toloka_token, 'PRODUCTION')

    pool_ids = read_pools_ids(pools_path)
    records = []
    for pool_id in pool_ids:
        pool = get_pool(pool_id, toloka_client)
        records.extend(pool)

    raw_records = records
    raw_header = ["result", "worker_id", "assignment_id"] + input_fields
    raw_records = [{key: r[key] for key in raw_header} for r in raw_records]

    write_jsonl(output_path, raw_records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-fields", type=str, default="first_url,second_url,first_text,second_text")
    parser.add_argument("--res-field", type=str, default="result")
    parser.add_argument("--token-path", type=str, default="~/.toloka/personal_token")
    parser.add_argument("--output-path", type=str, required=True)
    parser.add_argument("--pools-path", type=str, required=True)
    args = parser.parse_args()
    main(**vars(args))

