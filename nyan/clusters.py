import json
import os
import shutil
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from functools import cached_property

from jinja2 import Template

from nyan.client import MessageId
from nyan.document import Document
from nyan.mongo import get_clusters_collection
from nyan.title import choose_title
from nyan.openai import openai_completion


BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


class Cluster:
    def __init__(self):
        self.docs = list()
        self.url2doc = dict()
        self.clid = None
        self.is_important = False

        self.create_time = None
        self.messages = list()

        self.distances = None

        self.saved_annotation_doc = None
        self.saved_first_doc = None
        self.saved_hash = None
        self.saved_diff = None

    def add(self, doc):
        self.docs.append(doc)
        self.url2doc[doc.url] = doc

    def save_distances(self, distances):
        self.distances = distances

    def has(self, doc):
        return doc.url in self.url2doc

    def changed(self):
        return self.hash != self.saved_hash

    @property
    def pub_time(self):
        return self.first_doc.pub_time

    @cached_property
    def fetch_time(self):
        return max([doc.fetch_time for doc in self.docs])

    @property
    def views(self):
        return sum([doc.views for doc in self.docs])

    @property
    def debiased_views(self):
        views = [doc.views for doc in self.unique_docs]
        if len(views) <= 2:
            return sum(views)
        views.sort(reverse=True)

        # Smoothing outliers for cases where
        # one document has much more views than others
        views[0] = views[1]

        return sum(views)

    @property
    def age(self):
        return self.fetch_time - self.pub_time_percentile

    @property
    def views_per_hour(self):
        return int(self.debiased_views / (self.age / 3600))

    @property
    def embedding(self):
        return self.annotation_doc.embedding

    @cached_property
    def pub_time_percentile(self):
        timestamps = sorted([d.pub_time for d in self.docs])
        return timestamps[len(timestamps) // 5]

    @cached_property
    def images(self):
        image_doc_count = sum([1 if doc.images else 0 for doc in self.unique_docs])
        doc_count = len(self.unique_docs)
        if doc_count == 0:
            return tuple()
        images = [i["url"] for i in self.annotation_doc.embedded_images]
        if not images:
            return tuple()
        if image_doc_count / doc_count >= 0.4 or image_doc_count >= 3:
            return images
        return tuple()

    @cached_property
    def videos(self):
        videos = self.annotation_doc.videos
        if videos:
            return videos
        return tuple()

    @cached_property
    def cropped_title(self, max_words: int = 14):
        text = self.annotation_doc.patched_text
        words = text.split()
        if len(words) < max_words:
            return " ".join(words)
        return " ".join(words[:max_words]) + "..."

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
    def diff(self):
        if self.saved_diff is not None:
            return self.saved_diff

        prompt_path: Path = BASE_DIR / "prompts/diff.txt"
        with open(prompt_path) as f:
            template = Template(f.read())
        prompt = template.render(docs=self.docs, annotation_doc=self.annotation_doc)
        messages = [{"role": "user", "content": prompt}]

        try:
            result = openai_completion(messages=messages, model_name="gpt-4o")
            content = result.message.content.strip()
            content = content[content.find("{"):content.rfind("}") + 1]
            content = json.loads(content)
            differences = content["differences"]

            channel_titles = {doc.channel_id: doc.channel_title for doc in self.docs}
            doc_urls = {doc.channel_id: doc.url for doc in self.docs}
            for diff in differences:
                ids = diff["channel_ids"][:3]
                ids = [i for i in ids if i in channel_titles and i in doc_urls]
                channels = ['<a href="{}">{}</a>'.format(doc_urls[i], channel_titles[i]) for i in ids]
                diff["channels"] = ", ".join(channels)
        except Exception:
            differences = []
        return differences

    @property
    def annotation_doc(self):
        if self.saved_annotation_doc:
            return self.saved_annotation_doc
        self.saved_annotation_doc = choose_title(self.docs, self.issues)
        return self.saved_annotation_doc

    @cached_property
    def hash(self):  # noqa: A003
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
        groups = [doc.groups["main"] for doc in self.docs if doc.groups]
        if not groups:
            return None

        groups_count = Counter(groups)

        all_count = len(groups)
        blue_part = groups_count["blue"] / all_count
        red_part = groups_count["red"] / all_count

        if blue_part == 0.0 and red_part > 0.5:
            return "red"
        if red_part == 0.0 and blue_part > 0.5:
            return "blue"
        return "purple"

    @property
    def issues(self):
        if self.messages:
            return [m.issue for m in self.messages]

        def get_most_common(items):
            counter = Counter(items)
            max_count = counter.most_common(1)[0][1]
            return [item for item, count in counter.items() if count == max_count]

        issues = get_most_common([doc.issue for doc in self.docs])
        categories = get_most_common([doc.category for doc in self.docs])

        final_issues = ["main"]
        final_issues.extend(issues)
        final_issues.extend(categories)
        final_issues = set(final_issues)
        return list(final_issues)

    def get_issue_message(self, issue):
        messages = [m for m in self.messages if m.issue == issue]
        if messages:
            return messages[0]
        return None

    def get_url(self, host, issue):
        message = self.get_issue_message(issue)
        if not message:
            return None
        message_id = message.message_id
        return f"{host}/{message_id}"

    def asdict(self):
        docs = [d.asdict(is_short=True) for d in self.docs]
        annotation_doc = self.annotation_doc.asdict()
        first_doc = self.first_doc.asdict(is_short=True)
        return {
            "clid": self.clid,
            "docs": docs,
            "messages": [m.asdict() for m in self.messages],
            "annotation_doc": annotation_doc,
            "first_doc": first_doc,
            "hash": self.hash,
            "diff": self.diff,
            "is_important": self.is_important,
            "create_time": self.create_time
        }

    @classmethod
    def fromdict(cls, d):
        cluster = cls()
        cluster.clid = d.get("clid")

        for doc in d["docs"]:
            cluster.add(Document.fromdict(doc))

        if "message" in d:
            cluster.messages = [MessageId.fromdict(d["message"])]
        elif "messages" in d:
            cluster.messages = [MessageId.fromdict(m) for m in d["messages"]]
        elif "message_id" in d:
            cluster.messages = [MessageId(message_id=d["message_id"])]

        cluster.saved_annotation_doc = Document.fromdict(d.get("annotation_doc"))
        cluster.saved_first_doc = Document.fromdict(d.get("first_doc"))
        cluster.saved_hash = d.get("hash")
        cluster.saved_diff = d.get("diff", None)
        cluster.is_important = d.get("is_important", False)
        cluster.create_time = d.get("create_time", None)

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
        self.max_clid = 60000

    def find_similar(
        self,
        cluster,
        issue_name: str,
        min_size_ratio: float = 0.25,
        min_intersection_ratio: float = 0.25
    ):
        messages = list()
        for url in cluster.urls:
            message = self.urls2messages[issue_name].get(url)
            if message is None:
                continue
            messages.append(message)
        if not messages:
            return None

        message, intersection_count = Counter(messages).most_common()[0]
        old_cluster = self.message2cluster.get(message)
        if old_cluster is None:
            return None

        new_cluster_size = len(cluster.urls)
        old_cluster_size = len(old_cluster.urls)
        intersection_ratio = intersection_count / new_cluster_size
        intersection_ratio = min(intersection_ratio, intersection_count / old_cluster_size)
        size_ratio = new_cluster_size / old_cluster_size

        if size_ratio < min_size_ratio or intersection_ratio < min_intersection_ratio:
            return None
        return old_cluster

    def get_embedded_clusters(self, current_ts, issue):
        filtered_clusters = []
        for cluster in self.clid2cluster.values():
            if not cluster.embedding:
                continue
            if not cluster.messages:
                continue
            if abs(cluster.pub_time - current_ts) > 24 * 3600:
                continue
            if issue not in cluster.issues:
                continue
            filtered_clusters.append(cluster)
        return filtered_clusters

    def add(self, cluster):
        if cluster.clid is None:
            self.max_clid += 1
            cluster.clid = self.max_clid

        for message in cluster.messages:
            self.message2cluster[message] = cluster
        self.clid2cluster[cluster.clid] = cluster
        self.max_clid = max(self.max_clid, cluster.clid)

    def __len__(self):
        return len(self.clid2cluster)

    @cached_property
    def urls2messages(self):
        result = defaultdict(dict)
        for _, cluster in self.clid2cluster.items():
            for url in cluster.urls:
                for message in cluster.messages:
                    result[message.issue][url] = message
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
                if doc.patched_text == new_doc.patched_text and doc.views == new_doc.views:
                    continue
                cluster.docs[doc_index] = new_doc
                cluster.url2doc[url] = new_doc
                if cluster.saved_annotation_doc.url == url:
                    cluster.saved_annotation_doc = new_doc
                updates_count += 1
        return updates_count

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

    def save_to_mongo(self, mongo_config_path, only_new=True):
        collection = get_clusters_collection(mongo_config_path)
        if not self.clid2cluster:
            return 0
        max_cluster_fetch_time = max([cl.fetch_time for cl in self.clid2cluster.values()])
        saved_count = 0
        for clid, cluster in sorted(self.clid2cluster.items()):
            if only_new and max_cluster_fetch_time - cluster.fetch_time > 24 * 3600:
                continue
            saved_count += 1
            collection.replace_one({"clid": clid}, cluster.asdict(), upsert=True)
        return saved_count

    @classmethod
    def load_from_mongo(cls, mongo_config_path, current_ts, offset):
        collection = get_clusters_collection(mongo_config_path)
        clusters_dicts = list(collection.find({"create_time": {"$gte": current_ts - offset}}))
        clusters = cls()
        for cluster_dict in clusters_dicts:
            clusters.add(Cluster.fromdict(cluster_dict))
        return clusters
