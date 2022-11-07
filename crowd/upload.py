import argparse
import os
import datetime
import random

import toloka.client as toloka

from nyan.util import read_jsonl
from crowd.util import get_key, read_markup


def main(
    input_path,
    seed,
    token,
    existing_markup_path,
    honey_path,
    template_pool_id,
    overlap,
    page_size
):
    with open(os.path.expanduser(token), "r") as r:
        toloka_token = r.read().strip()

    random.seed(seed)
    existing_records = read_jsonl(existing_markup_path) if existing_markup_path else []
    existing_keys = {get_key(r, ("first_url", "second_url")) for r in existing_records}

    honey_records = read_markup(honey_path)
    honeypots = []
    input_fields = [
        "first_url", "second_url",
        "first_text", "second_text"
    ]
    output_fields = ["result"]

    for r in honey_records:
        input_values = {field: r[field] for field in input_fields}
        output_values = {field: r[field] for field in output_fields}
        task = toloka.task.Task(
            input_values=input_values,
            known_solutions=[{"output_values": output_values}]
        )
        honeypots.append(task)
    assert len(honeypots) == 40

    input_records = read_jsonl(input_path)
    input_records = {get_key(r, ("first_url", "second_url")): r for r in input_records}
    input_records = list(input_records.values())
    tasks = []
    for r in input_records:
        if get_key(r, ("first_url", "second_url")) in existing_keys:
            continue
        input_values = {field: r[field] for field in input_fields}
        task = toloka.task.Task(input_values=input_values)
        tasks.append(task)

    random.shuffle(honeypots)
    random.shuffle(tasks)
    target_honeypots_count = len(tasks) // 9
    full_honeypots = honeypots[:target_honeypots_count]
    while len(full_honeypots) < target_honeypots_count:
        full_honeypots += honeypots
    honeypots = full_honeypots[:target_honeypots_count]
    assert len(honeypots) == 40
    tasks.extend(honeypots)
    random.shuffle(tasks)

    toloka_client = toloka.TolokaClient(toloka_token, 'PRODUCTION')
    template_pool = toloka_client.get_pool(template_pool_id)
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    template_pool.private_name = "Pool: " + current_date
    pool = toloka_client.create_pool(template_pool)

    task_suites = []
    start_index = 0
    while start_index < len(tasks):
        task_suite = tasks[start_index: start_index+page_size]
        ts = toloka.task_suite.TaskSuite(
            pool_id=pool.id,
            tasks=task_suite,
            overlap=overlap
        )
        task_suites.append(ts)
        start_index += page_size

    task_suites = toloka_client.create_task_suites(task_suites)
    toloka_client.open_pool(pool.id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", type=str, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--token", type=str, default="~/.toloka/personal_token")
    parser.add_argument("--existing-markup-path", type=str, default=None)
    parser.add_argument("--honey-path", type=str, required=True)
    parser.add_argument("--template-pool-id", type=int, required=True)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--overlap", type=int, default=5)
    args = parser.parse_args()
    main(**vars(args))
