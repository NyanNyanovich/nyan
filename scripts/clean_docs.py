import argparse
import json
from tqdm import tqdm

from nyan.annotator import Annotator
from nyan.document import Document
from nyan.channels import Channels


def main(
    input_path,
    output_path,
    annotator_config,
    channels_path,
    rm_fields,
    min_pub_time,
    batch_size
):
    rm_fields = rm_fields.split(",")
    channels = Channels(channels_path)
    annotator = Annotator(annotator_config, channels)
    annotator.embedder = None
    annotator.image_processor = None

    def process_batch(batch, fh):
        clean_docs = annotator(batch)
        for doc in clean_docs:
            if doc.is_discarded():
                continue
            doc = doc.asdict()
            for field in rm_fields:
                doc.pop(field, None)
            fh.write(json.dumps(doc, ensure_ascii=False).strip() + "\n")

    batch = []
    with open(input_path) as r, open(output_path, "w") as w:
        for line in tqdm(r):
            doc = Document.fromdict(json.loads(line))
            if min_pub_time and doc.pub_time < min_pub_time:
                continue
            batch.append(doc)
            if len(batch) == batch_size:
                process_batch(batch, w)
                batch = []
        if batch:
            process_batch(batch, w)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, required=True)
    parser.add_argument("--input-path", type=str, required=True)
    parser.add_argument("--annotator-config", type=str, default="configs/annotator_config.json")
    parser.add_argument("--channels-path", type=str, default="channels.json")
    parser.add_argument("--rm-fields", type=str, default="embedding,category")
    parser.add_argument("--min-pub-time", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    main(**vars(args))
