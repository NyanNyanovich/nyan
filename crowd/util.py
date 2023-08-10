import os
import hashlib


def get_key(r, key_fields):
    return tuple(sorted((r[key_field] for key_field in key_fields)))


def get_pool(pool_id, toloka_client, include_honey: bool = False):
    records = []
    for assignment in toloka_client.get_assignments(pool_id=pool_id):
        solutions = assignment.solutions
        if not solutions:
            continue
        for task, solution in zip(assignment.tasks, solutions):
            known_solutions = task.known_solutions
            if known_solutions is not None and not include_honey:
                continue
            input_values = task.input_values
            output_values = solution.output_values
            record = {
                "worker_id": assignment.user_id,
                "assignment_id": assignment.id
            }
            record.update(input_values)
            record.update(output_values)
            records.append(record)
    return records


def read_markup(markup_path):
    records = []
    with open(markup_path, "r") as r:
        header = next(r).strip().split("\t")
        header = [f.split(":")[-1] for f in header]
        for line in r:
            fields = line.strip().split("\t")
            record = dict(zip(header, fields))
            records.append(record)
    return records


def read_token(token_path):
    token_path = os.path.expanduser(token_path)
    assert os.path.exists(token_path)
    with open(token_path, "r") as r:
        toloka_token = r.read().strip()
    return toloka_token


def read_pools_ids(pools_path):
    pool_ids = []
    with open(pools_path, "r") as r:
        for line in r:
            pool_id = line.strip()
            if not pool_id:
                continue
            pool_ids.append(int(pool_id))
    return pool_ids
