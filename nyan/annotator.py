import json
import re
from typing import List
from urllib.parse import unquote, urlparse

from tqdm import tqdm

from nyan.channels import Channels
from nyan.document import Document
from nyan.fasttext import FasttextClassifier
from nyan.labse import Embedder
from nyan.text import TextProcessor
from nyan.tokenizer import Tokenizer


class Annotator:
    def __init__(self, config_path, channels: Channels):
        with open(config_path) as r:
            config = json.load(r)

        self.embedder = Embedder(config["model_name"])
        self.text_processor = TextProcessor(config["text_processor"])
        self.tokenizer = Tokenizer(**config.get("tokenizer", {}))

        self.lang_detector = None
        if "lang_detector" in config:
            self.lang_detector = FasttextClassifier(config["lang_detector"])

        self.cat_detector = None
        if "cat_detector" in config:
            self.cat_detector = FasttextClassifier(config["cat_detector"], use_tokenizer=True, lower=True)

        self.channels = channels

    def __call__(self, docs: List[Document]) -> List[Document]:
        pipeline = (
            self.process_channels_info,
            self.clean_text,
            self.tokenize,
            self.normalize_links,
            self.has_obscene,
            self.predict_language,
            self.predict_category
        )
        filtered_docs = list()
        for doc in tqdm(docs, desc="Annotator pipeline"):
            for step in pipeline:
                doc = step(doc)
                if doc is None:
                    break
            if doc is not None:
                filtered_docs.append(doc)
        docs = filtered_docs

        if self.embedder is not None:
            docs = self.calc_embeddings(docs)
        return docs

    def process_channels_info(self, doc):
        channel_id = doc.channel_id.strip().lower()
        if channel_id not in self.channels:
            return None

        channel_info = self.channels[channel_id]
        doc.groups = channel_info.groups
        doc.issue = channel_info.issue

        channel_alias = channel_info.alias
        if channel_alias:
            doc.channel_title = channel_alias
        return doc

    def clean_text(self, doc):
        text = self.text_processor(doc.text)
        if not text or len(text) < 10:
            return None
        doc.patched_text = text
        return doc

    def tokenize(self, doc):
        tokens = self.tokenizer(doc.patched_text)
        tokens = ["{}_{}".format(t.lemma.lower().replace("_", ""), t.pos) for t in tokens]
        doc.tokens = " ".join(tokens)
        return doc

    def normalize_links(self, doc):
        def has_cyrillic(text):
            return bool(re.search("[а-яА-Я]", text))

        fixed_links = []
        for link in doc.links:
            decoded_link = unquote(link)
            parsed_link = urlparse(decoded_link)
            host = parsed_link.netloc
            if not host:
                continue
            if has_cyrillic(host) and host.split(".")[-1] != "рф":
                continue
            fixed_links.append(decoded_link)
        doc.links = fixed_links
        return doc

    def has_obscene(self, doc):
        doc.has_obscene = self.text_processor.has_obscene(doc.patched_text)
        return doc

    def calc_embeddings(self, docs):
        texts = [d.text for d in docs]
        embeddings = self.embedder(texts)
        for d, embedding in zip(docs, embeddings):
            d.embedding = embedding.numpy().tolist()
        return docs

    def predict_language(self, doc):
        if not self.lang_detector:
            return doc
        language, prob = self.lang_detector(doc.patched_text)
        doc.language = language
        return doc

    def predict_category(self, doc):
        if not self.cat_detector:
            return doc
        category, prob = self.cat_detector(doc.patched_text)
        doc.category = category
        if category == "not_news":
            return None
        return doc
