import json
import os
import shutil
import hashlib
from collections import Counter
from functools import cached_property
from statistics import mean

from scipy.spatial.distance import cosine

from nyan.document import Document
from nyan.mongo import get_clusters_collection


class Cluster:
    def __init__(self):
        self.docs = list()
        self.url2doc = dict()
        self.message_id = None
        self.create_time = None
        self.is_important = False

        self.saved_annotation_doc = None
        self.saved_first_doc = None
        self.saved_hash = None

    def add(self, doc):
        self.docs.append(doc)
        self.url2doc[doc.url] = doc

    def has(self, doc):
        return doc.url in self.url2doc

    def changed(self):
        return self.hash != self.saved_hash

    # Computable properties
    @property
    def pub_time(self):
        return self.first_doc.pub_time

    @property
    def fetch_time(self):
        return max([doc.fetch_time for doc in self.docs])

    @cached_property
    def views(self):
        return sum([doc.views for doc in self.docs])

    @cached_property
    def views_str(self):
        if self.views >= 1000000:
            return "{:.1f}M".format(self.views / 1000000).replace(".", ",")
        elif self.views >= 1000:
            return "{:.1f}K".format(self.views / 1000).replace(".", ",")
        return self.views

    @property
    def age(self):
        return self.fetch_time - self.pub_time_percentile

    @property
    def views_per_hour(self):
        return int(self.views / (self.age / 3600))

    @cached_property
    def pub_time_percentile(self):
        timestamps = [d.pub_time for d in self.docs]
        timestamps.sort()
        n = len(timestamps)
        index = n // 5
        return timestamps[index]

    @cached_property
    def images(self):
        image_doc_count = sum([1 if doc.images else 0 for doc in self.docs])
        images = self.annotation_doc.images
        if images and image_doc_count >= 3:
            return images
        return tuple()

    @cached_property
    def videos(self):
        videos = self.annotation_doc.videos
        if videos:
            return videos
        return tuple()

    @cached_property
    def cropped_title(self):
        return " ".join(self.annotation_doc.text.split()[:10]) + "..."

    @property
    def urls(self):
        return list(self.url2doc.keys())

    @property
    def channels(self):
        return list({d.channel_id for d in self.docs})

    @property
    def first_doc(self):
        if self.saved_first_doc:
            return self.saved_first_doc
        return min(self.docs, key=lambda x: x.pub_time)

    @property
    def annotation_doc(self):
        if self.saved_annotation_doc:
            return self.saved_annotation_doc

        docs = self.docs

        avg_distances = dict()
        for doc1 in docs:
            distances = [cosine(doc1.embedding, doc2.embedding) for doc2 in docs]
            avg_distances[doc1.url] = mean(distances)

        filtered_docs = [d for d in docs if d.language == "ru"]
        if filtered_docs:
            docs = filtered_docs

        filtered_docs = [d for d in docs if len(d.text) < 400]
        if filtered_docs:
            docs = filtered_docs

        filtered_docs = [d for d in docs if abs(d.fetch_time - d.pub_time) < 3600]
        if filtered_docs:
            docs = filtered_docs

        filtered_docs = [d for d in docs if d.group == "purple"]
        if len(filtered_docs) >= 2:
            docs = filtered_docs

        self.saved_annotation_doc = min(docs, key=lambda x: avg_distances[x.url])
        return self.saved_annotation_doc

    @cached_property
    def hash(self):
        data = " ".join(sorted({d.channel_id for d in self.docs}))
        data += " " + self.views_str
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @property
    def external_links(self):
        links = Counter()
        for doc in self.docs:
            for link in doc.links:
                if "t.me" not in link and "http" in link:
                    links[link] += 1
        return links

    @property
    def group(self):
        channels = {doc.channel_id: doc.group for doc in self.docs}
        groups_count = Counter(list(channels.values()))

        all_count = len(channels)
        blue_count = groups_count["blue"]
        red_count = groups_count["red"]
        purple_count = groups_count["purple"]
        blue_part = blue_count / all_count
        red_part = red_count / all_count
        purple_part = purple_count / all_count

        if blue_part + purple_part >= 0.85:
            return "blue"
        if red_part + purple_part >= 0.85:
            return "red"
        return "purple"

    # Serialization
    def asdict(self):
        return {
            "docs": [d.asdict() for d in self.docs],
            "message_id": self.message_id,
            "create_time": self.create_time,
            "annotation_doc": self.annotation_doc.asdict(),
            "first_doc": self.first_doc.asdict(),
            "hash": self.hash,
            "is_important": self.is_important
        }

    def serialize(self):
        return json.dumps(self.asdict())

    @classmethod
    def fromdict(cls, d):
        cluster = cls()
        for doc in d["docs"]:
            cluster.add(Document.fromdict(doc))
        cluster.message_id = d["message_id"]
        cluster.create_time = d.get("create_time")
        cluster.saved_annotation_doc = Document.fromdict(d.get("annotation_doc"))
        cluster.saved_first_doc = Document.fromdict(d.get("first_doc"))
        cluster.saved_hash = d.get("hash")
        cluster.is_important = d.get("is_important", False)
        return cluster

    @classmethod
    def deserialize(cls, line):
        d = json.loads(line)
        return cls.fromdict(d)


class Clusters:
    def __init__(self):
        self.clusters = dict()

    def __getitem__(self, message_id):
        return self.clusters[message_id]

    def __setitem__(self, message_id, cluster):
        self.clusters[message_id] = cluster

    def __len__(self):
        return len(self.clusters)

    def __iter__(self):
        return iter(self.clusters)

    def items(self):
        return self.clusters.items()

    @cached_property
    def urls2messages(self):
        return {url: message_id for message_id, cl in self.clusters.items() for url in cl.urls}

    def update_documents(self, documents):
        url2doc = {doc.url: doc for doc in documents}
        updates_count = 0
        for _, cluster in self.clusters.items():
            for doc_index, doc in enumerate(cluster.docs):
                url = doc.url
                if url not in url2doc:
                    continue
                new_doc = url2doc[url]
                if doc.text == new_doc.text and doc.views == new_doc.views:
                    continue
                cluster.docs[doc_index] = new_doc
                cluster.url2doc[url] = new_doc
                if cluster.saved_annotation_doc.url == url:
                    cluster.saved_annotation_doc = new_doc
                updates_count += 1
        return updates_count

    # Serialization
    def save(self, path):
        temp_path = path + ".new"
        with open(path + ".new", "w") as w:
            for _, cluster in sorted(self.clusters.items()):
                w.write(cluster.serialize() + "\n")
        shutil.move(temp_path, path)

    @classmethod
    def load(cls, path):
        assert os.path.exists(path)
        clusters = cls()
        with open(path) as r:
            for line in r:
                cluster = Cluster.deserialize(line)
                clusters.clusters[cluster.message_id] = cluster
        return clusters

    def save_to_mongo(self, mongo_config_path):
        collection = get_clusters_collection(mongo_config_path)
        for _, cluster in sorted(self.clusters.items()):
            collection.replace_one({"message_id": cluster.message_id}, cluster.asdict(), upsert=True)

    @classmethod
    def load_from_mongo(cls, mongo_config_path):
        collection = get_clusters_collection(mongo_config_path)
        clusters_dicts = list(collection.find({}))
        clusters = cls()
        for cluster_dict in clusters_dicts:
            cluster = Cluster.fromdict(cluster_dict)
            clusters.clusters[cluster.message_id] = cluster
        return clusters
