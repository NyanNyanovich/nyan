from sklearn.metrics.pairwise import cosine_similarity

from nyan.clip import ClipEmbedder
from nyan.image import ImageProcessor

def test_clip(clip_data):
    texts = [r["en_text"] for r in clip_data]
    images = [r["image"] for r in clip_data]
    embedder = ClipEmbedder()
    images = embedder.fetch_images(images)
    text_embeddings = embedder.embed_texts(texts)
    image_embeddings = embedder.embed_images([i["content"] for i in images])
    similarity = cosine_similarity(text_embeddings, image_embeddings)
    for i, (text, image) in enumerate(zip(texts, images)):
        best_index = similarity[i].argmax()
        assert best_index == i, \
            f"CLIP: {text} vs {image} mismath, matching image: {images[best_index]}"


def test_image_processor(clip_data, annotator):
    images = [r["image"] for r in clip_data]

    embedder = ClipEmbedder()
    fetched_images = embedder.fetch_images(images)
    image_embeddings = embedder.embed_images([i["content"] for i in fetched_images])

    embedded_images = annotator.image_processor(images)
    for embedded_image, embedding in zip(embedded_images, image_embeddings):
        assert embedded_image["embedding"] == embedding.tolist()
