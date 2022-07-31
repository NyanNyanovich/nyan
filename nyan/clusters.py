import json
import os
import shutil
import hashlib
from collections import Counter, defaultdict
from functools import cached_property
from dataclasses import dataclass

from nyan.document import Document
from nyan.mongo import get_clusters_collection
from nyan.title import choose_title
from nyan.util import Serializable


@dataclass
class Message(Serializable):
    message_id: int
    issue: str
    create_time: int

    def as_tuple(self):
        return (self.issue, self.message_id)

    def __hash__(self):
        return hash(self.as_tuple())

    def __eq__(self, another):
        return self.as_tuple() == another.self.as_tuple()


class Cluster:
    def __init__(self):
        self.docs = list()
        self.url2doc = dict()
        self.clid = None
        self.is_important = False

        self.message = None

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

    def set_message(self, *args, **kwargs):
        self.message = Message(*args, **kwargs)

    @property
    def pub_time(self):
        return self.first_doc.pub_time

    @cached_property
    def fetch_time(self):
        return max([doc.fetch_time for doc in self.docs])

    @cached_property
    def views(self):
        return sum([doc.views for doc in self.docs])

    @property
    def age(self):
        return self.fetch_time - self.pub_time_percentile

    @property
    def views_per_hour(self):
        return int(self.views / (self.age / 3600))

    @cached_property
    def pub_time_percentile(self):
        timestamps = list(sorted([d.pub_time for d in self.docs]))
        return timestamps[len(timestamps) // 5]

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
        self.saved_annotation_doc = choose_title(self.docs)
        return self.saved_annotation_doc

    @cached_property
    def hash(self):
        data = " ".join(sorted({d.channel_id for d in self.docs}))
        data += " " + str(self.views // 100000)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @property
    def unique_docs(self):
        return [doc for doc in self.docs if not doc.forward_from]

    @property
    def external_links(self):
        links = Counter()
        used_channels = set()
        for doc in self.unique_docs:
            doc_links = set(doc.links)
            if doc.channel_id in used_channels:
                continue
            for link in doc_links:
                if "t.me" not in link and "http" in link:
                    links[link] += 1
                    used_channels.add(doc.channel_id)
        return links

    @property
    def group(self):
        channels = {doc.channel_id: doc.group for doc in self.docs}
        groups_count = Counter(list(channels.values()))

        all_count = len(channels)
        blue_part = groups_count["blue"] / all_count
        red_part = groups_count["red"] / all_count

        if blue_part == 0.0 and red_part > 0.5:
            return "red"
        if red_part == 0.0 and blue_part > 0.5:
            return "blue"
        return "purple"

    def asdict(self):
        return {
            "clid": self.clid,
            "docs": [d.asdict() for d in self.docs],
            "message": self.message.asdict(),
            "annotation_doc": self.annotation_doc.asdict(),
            "first_doc": self.first_doc.asdict(),
            "hash": self.hash,
            "is_important": self.is_important
        }

    @classmethod
    def fromdict(cls, d):
        cluster = cls()
        cluster.clid = d.get("clid")

        for doc in d["docs"]:
            cluster.add(Document.fromdict(doc))

        cluster.message = Message.fromdict(d.get("message"))
        if not cluster.message and "message_id" in d and "create_time" in d:
            cluster.message = Message(message_id=d["message_id"], issue="main", create_time=d["create_time"])

        cluster.saved_annotation_doc = Document.fromdict(d.get("annotation_doc"))
        cluster.saved_first_doc = Document.fromdict(d.get("first_doc"))
        cluster.saved_hash = d.get("hash")
        cluster.is_important = d.get("is_important", False)

        return cluster

    def serialize(self):
        return json.dumps(self.asdict(), ensure_ascii=False)

    @classmethod
    def deserialize(cls, line):
        return cls.fromdict(json.loads(line))


class Clusters:
    def __init__(self):
        self.clid2cluster = dict()
        self.message2cluster = dict()
        self.max_clid = 0

    def find_similar(self, cluster):
        messages = [self.urls2messages.get(url) for url in cluster.urls if url in self.urls2messages]
        if not messages:
            return None
        message = Counter(messages).most_common()[0][0]
        return self.message2cluster.get(message)

    def add(self, cluster):
        if cluster.clid is None:
            self.max_clid += 1
            cluster.clid = self.max_clid

        self.message2cluster[cluster.message] = cluster
        self.clid2cluster[cluster.clid] = cluster
        self.max_clid = max(self.max_clid, cluster.clid)

    def __len__(self):
        return len(self.clid2cluster)

    @cached_property
    def urls2messages(self):
        result = dict()
        for _, cluster in self.clid2cluster.items():
            for url in cluster.urls:
                result[url] = cluster.message
        return result

    def update_documents(self, documents):
        url2doc = {doc.url: doc for doc in documents}
        updates_count = 0
        for _, cluster in self.clid2cluster.items():
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
            for _, cluster in sorted(self.clid2cluster.items()):
                w.write(cluster.serialize() + "\n")
        shutil.move(temp_path, path)

    @classmethod
    def load(cls, path):
        assert os.path.exists(path)
        clusters = cls()
        with open(path) as r:
            for line in r:
                clusters.add(Cluster.deserialize(line))
        return clusters

    def save_to_mongo(self, mongo_config_path):
        collection = get_clusters_collection(mongo_config_path)
        for clid, cluster in sorted(self.clid2cluster.items()):
            collection.replace_one({"clid": clid}, cluster.asdict(), upsert=True)

    @classmethod
    def load_from_mongo(cls, mongo_config_path):
        collection = get_clusters_collection(mongo_config_path)
        clusters_dicts = list(collection.find({}))
        clusters = cls()
        for cluster_dict in clusters_dicts:
            clusters.add(Cluster.fromdict(cluster_dict))
        return clusters
