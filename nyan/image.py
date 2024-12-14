from typing import Dict, Any, List

from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
from PIL import Image

from nyan.clip import ClipEmbedder


class ImageProcessor:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.clip_embedder = ClipEmbedder()
        self.rm_threshold = config["rm_threshold"]

        rm_images_urls: List[str] = config["rm_images"]
        rm_images_dicts = self.clip_embedder.fetch_images(rm_images_urls)
        rm_images: List[Image.Image] = [i["content"] for i in rm_images_dicts]
        self.rm_embeddings = self.clip_embedder.embed_images(rm_images)

    def __call__(self, images: List[str]) -> List[Dict[str, Any]]:
        fetched_images = self.clip_embedder.fetch_images(images)
        if not fetched_images:
            return []
        contents: List[Image.Image] = [i["content"] for i in fetched_images]
        image_embeddings = self.clip_embedder.embed_images(contents)
        rm_scores = cosine_similarity(image_embeddings, self.rm_embeddings)
        rm_scores = rm_scores.max(axis=1)
        assert len(rm_scores) == len(fetched_images)
        embedded_images = []
        for image, embedding, rm_score in zip(
            fetched_images, image_embeddings, rm_scores
        ):
            if rm_score > self.rm_threshold:
                continue
            embedded_images.append(
                {"url": image["url"], "embedding": embedding.tolist()}
            )
        return embedded_images
