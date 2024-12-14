import json
import re
from typing import List
from urllib.parse import unquote, urlparse
import numpy as np

from tqdm import tqdm

from nyan.channels import Channels
from nyan.document import Document
from nyan.fasttext_clf import FasttextClassifier
from nyan.classifier import ClassifierHead
from nyan.embedder import Embedder
from nyan.text import TextProcessor
from nyan.image import ImageProcessor
from nyan.tokenizer import Tokenizer


class Annotator:
    def __init__(self, config_path: str, channels: Channels):
        assert isinstance(channels, Channels), "Wrong channels argument in Annotator"
        with open(config_path) as r:
            config = json.load(r)

        self.embedder = Embedder(**config["embedder"])
        self.text_processor = TextProcessor(config["text_processor"])
        self.tokenizer = Tokenizer(**config.get("tokenizer", {}))

        self.image_processor = None
        if "image_processor" in config:
            self.image_processor = ImageProcessor(config["image_processor"])

        self.lang_detector = None
        if "lang_detector" in config:
            self.lang_detector = FasttextClassifier(config["lang_detector"])

        self.cat_detector = None
        if "cat_detector" in config:
            self.cat_detector = ClassifierHead(config["cat_detector"])

        self.channels = channels

    def __call__(self, docs: List[Document]) -> List[Document]:
        pre_pipeline = (
            self.process_channels_info,
            self.clean_text,
            self.tokenize,
            self.normalize_links,
            self.has_obscene,
            self.predict_language,
            self.process_images,
        )
        processed_docs = list()
        for doc in tqdm(docs, desc="Annotator pre-embeddings pipeline"):
            for step in pre_pipeline:
                doc = step(doc)
            processed_docs.append(doc)
        docs = processed_docs

        if self.embedder is not None:
            docs = self.calc_embeddings(docs)

        post_pipeline = (self.predict_category,)
        processed_docs = list()
        for doc in tqdm(docs, desc="Annotator post-embeddings pipeline"):
            for step in post_pipeline:
                doc = step(doc)
            processed_docs.append(doc)
        return processed_docs

    def postprocess(self, docs: List[Document]) -> List[Document]:
        return [doc for doc in docs if not doc.is_discarded()]

    def process_channels_info(self, doc: Document) -> Document:
        channel_id = doc.channel_id.strip().lower()
        if channel_id not in self.channels:
            return doc

        channel_info = self.channels[channel_id]
        doc.groups = channel_info.groups
        doc.issue = channel_info.issue

        channel_alias = channel_info.alias
        if channel_alias:
            doc.channel_title = channel_alias
        return doc

    def clean_text(self, doc: Document) -> Document:
        if not doc.text:
            return doc
        doc.patched_text = self.text_processor(doc.text)
        return doc

    def tokenize(self, doc: Document) -> Document:
        if not doc.patched_text:
            return doc
        tokens = self.tokenizer(doc.patched_text)
        tokens = [
            "{}_{}".format(t.lemma.lower().replace("_", ""), t.pos) for t in tokens
        ]
        doc.tokens = " ".join(tokens)
        return doc

    def normalize_links(self, doc: Document) -> Document:
        def has_cyrillic(text: str) -> bool:
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

    def has_obscene(self, doc: Document) -> Document:
        if not doc.patched_text:
            return doc
        doc.has_obscene = self.text_processor.has_obscene(doc.patched_text)
        return doc

    def calc_embeddings(self, docs: List[Document]) -> List[Document]:
        ready_docs = [d for d in docs if d.patched_text is not None]
        texts = [d.patched_text for d in ready_docs]
        embeddings = self.embedder(texts)
        for d, embedding in zip(ready_docs, embeddings):
            d.embedding = embedding.numpy().tolist()
        return ready_docs

    def predict_language(self, doc: Document) -> Document:
        if not self.lang_detector:
            return doc
        if not doc.patched_text:
            return doc
        language, prob = self.lang_detector(doc.patched_text)
        doc.language = language
        return doc

    def predict_category(self, doc: Document) -> Document:
        if not self.cat_detector:
            return doc
        if not doc.patched_text:
            return doc
        if not doc.embedding:
            return doc
        category, scores = self.cat_detector(doc.embedding, doc.embedding_key)
        doc.category_scores = scores
        doc.category = category
        return doc

    def process_images(self, doc: Document) -> Document:
        if not self.image_processor:
            return doc
        doc.embedded_images = self.image_processor(list(doc.images))
        return doc
