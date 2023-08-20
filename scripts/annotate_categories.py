import argparse
import random
import json

from jinja2 import Template
from tqdm import tqdm

from nyan.util import read_jsonl, gen_batch, write_jsonl
from nyan.openai import openai_batch_completion


def process_text(text, max_words: int = 100):
    words = text.split()
    words = [w for w in words if w]
    if len(words) > max_words:
        text = " ".join(words[:max_words])
        text += "..."
        return text
    return " ".join(words)


def annotate_categories(
    documents,
    prompt_template,
    model_name
):
    prompts = []
    for document in tqdm(documents):
        text = document["patched_text"]
        text = process_text(text)
        prompt = prompt_template.render(text=text).strip() + "\n"
        prompts.append(prompt)

    document_index = 0
    for batch in tqdm(gen_batch(prompts, batch_size=1)):
        batch = [[{"role": "user", "content": prompt}] for prompt in batch]
        results = openai_batch_completion(batch, model_name=model_name)
        for result in results:
            print("Text:", process_text(documents[document_index]["patched_text"]))
            content = result.message.content.strip()
            print("Answer:", content)
            print()
            print()
            content = content[content.find("["):content.rfind("]") + 1]
            categories = json.loads(content)
            documents[document_index]["categories"] = categories
            yield documents[document_index]
            document_index += 1


def main(
    documents_path,
    output_path,
    prompt_path,
    model_name,
    sample_rate,
    seed
):
    random.seed(seed)
    documents = list(read_jsonl(documents_path, sample_rate))
    with open(prompt_path) as f:
        prompt_template = Template(f.read())

    with open(output_path, "a") as w:
        for doc in annotate_categories(documents, prompt_template, model_name):
            w.write(json.dumps(doc, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--documents-path", type=str, required=True)
    parser.add_argument("--prompt-path", type=str, required=True)
    parser.add_argument("--output-path", type=str, required=True)
    parser.add_argument("--model-name", type=str, default="gpt-4")
    parser.add_argument("--sample-rate", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()
    main(**vars(args))
