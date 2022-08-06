import argparse
import json

from nyan.annotator import Annotator
from nyan.document import Document


def main(
    input_path,
    output_path,
    annotator_config,
    channels_path,
    rm_fields,
    min_pub_time
):
    rm_fields = rm_fields.split(",")
    annotator = Annotator(annotator_config, channels_path)
    annotator.embedder = None

    with open(input_path) as r, open(output_path, "w") as w:
        docs = [Document.fromdict(json.loads(line)) for line in r]
        clean_docs = annotator(docs)
        clean_docs = [doc for doc in clean_docs if not min_pub_time or doc.pub_time >= min_pub_time]
        clean_docs.sort(key=lambda x: x.pub_time)

        for doc in clean_docs:
            doc = doc.asdict()
            for field in rm_fields:
                doc.pop(field, None)
            w.write(json.dumps(doc, ensure_ascii=False).strip() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", type=str, required=True)
    parser.add_argument("--input-path", type=str, required=True)
    parser.add_argument("--annotator-config", type=str, default="configs/annotator_config.json")
    parser.add_argument("--channels-path", type=str, default="channels.json")
    parser.add_argument("--rm-fields", type=str, default="embedding,category")
    parser.add_argument("--min-pub-time", type=int, default=None)
    args = parser.parse_args()
    main(**vars(args))
