from typing import Callable, Dict, List

import numpy as np
import requests
import torch
from transformers import CLIPProcessor, CLIPModel, AutoTokenizer
from tqdm.auto import tqdm
from PIL import Image

from nyan.util import set_random_seed, gen_batch


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEFAULT_CLIP_PATH = "openai/clip-vit-base-patch32"


class ClipEmbedder:
    def __init__(self,
        model_name: str = DEFAULT_CLIP_PATH,
        normalize: bool = True,
        image_batch_size: int = 16,
        text_batch_size: int = 32,
        device: str = DEVICE
    ):
        self.model_name = model_name
        self.model = CLIPModel.from_pretrained(model_name).to(device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.image_batch_size = image_batch_size
        self.text_batch_size = text_batch_size
        self.normalize = normalize

    def embed_images(self, images_paths: List[str]) -> np.ndarray:
        return self._calc_embeddings(
            func=self._process_images_batch,
            inputs=images_paths,
            batch_size=self.image_batch_size,
            desc="CLIP image embeddings"
        )

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        return self._calc_embeddings(
            func=self._process_texts_batch,
            inputs=texts,
            batch_size=self.text_batch_size,
            desc="CLIP text embeddings"
        )

    def _calc_embeddings(
        self,
        func: Callable,
        inputs: List[str],
        batch_size: int,
        desc: str
    ) -> np.ndarray:
        embeddings = torch.zeros((len(inputs), self.model.projection_dim))
        total = len(inputs) // batch_size + 1
        for batch_num, batch in tqdm(enumerate(gen_batch(inputs, batch_size)), total=total, desc=desc):
            with torch.no_grad():
                batch_embeddings = func(batch)
            start_index = batch_num * batch_size
            end_index = (batch_num + 1) * batch_size
            embeddings[start_index:end_index, :] = batch_embeddings
        if self.normalize:
            embeddings /= embeddings.norm(dim=-1, keepdim=True)
        return embeddings.numpy()

    def _process_images_batch(self, images_paths: List[str]) -> Dict[str, torch.tensor]:
        images = []
        for path in images_paths:
            if path.startswith("http://") or path.startswith("https://"):
                path = requests.get(path, stream=True).raw
            images.append(Image.open(path))
        inputs = self.processor(images=images, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        return self.model.get_image_features(**inputs)

    def _process_texts_batch(self, texts: List[str]) -> Dict[str, torch.tensor]:
        inputs = self.processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        return self.model.get_text_features(**inputs)
