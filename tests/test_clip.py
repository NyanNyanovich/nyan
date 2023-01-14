from sklearn.metrics.pairwise import cosine_similarity

from nyan.clip import ClipEmbedder

def test_clip(clip_data):
    texts = [r["en_text"] for r in clip_data]
    images = [r["image"] for r in clip_data]
    embedder = ClipEmbedder()
    text_embeddings = embedder.embed_texts(texts)
    image_embeddings = embedder.embed_images(images)
    similarity = cosine_similarity(text_embeddings, image_embeddings)
    for i, (text, image) in enumerate(zip(texts, images)):
        best_index = similarity[i].argmax()
        assert best_index == i, \
            f"CLIP: {text} vs {image} mismath, matching image: {images[best_index]}"
