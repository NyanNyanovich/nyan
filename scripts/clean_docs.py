import json
import sys
from nyan.annotator import Annotator
from nyan.document import Document

input_path = sys.argv[1]
output_path = sys.argv[2]

annotator = Annotator("configs/annotator_config.json", "channels.json")

with open(input_path) as r, open(output_path, "w") as w:
    docs = [Document.fromdict(json.loads(line)) for line in r]
    clean_docs = annotator(docs)
    for doc in clean_docs:
        w.write(json.dumps(doc.asdict(save_embedding=True), ensure_ascii=False).strip() + "\n")
