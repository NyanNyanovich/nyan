from typing import TypeVar, Callable, Dict, List, Any, cast

import numpy as np
from numpy.typing import NDArray
import requests
import torch
from transformers import CLIPProcessor, CLIPModel  # type: ignore
from tqdm.auto import tqdm
from PIL import Image

from nyan.util import gen_batch


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEFAULT_CLIP_PATH = "openai/clip-vit-base-patch32"
T = TypeVar("T")


class ClipEmbedder:
    def __init__(
        self,
        model_name: str = DEFAULT_CLIP_PATH,
        normalize: bool = True,
        image_batch_size: int = 16,
        text_batch_size: int = 32,
        device: str = DEVICE,
        enable_tqdm: bool = False,
    ):
        self.model_name = model_name
        self.model = CLIPModel.from_pretrained(model_name).to(device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.image_batch_size = image_batch_size
        self.text_batch_size = text_batch_size
        self.normalize = normalize
        self.enable_tqdm = enable_tqdm

    def fetch_images(self, urls: List[str]) -> List[Dict[str, Any]]:
        images = []
        for url in urls:
            if not url.startswith("http://") and not url.startswith("https://"):
                continue
            try:
                response = requests.get(url, stream=True)
            except Exception:
                continue
            if response.status_code != 200:
                continue
            images.append({"url": url, "content": Image.open(response.raw)})
        return images

    def embed_images(self, images: List[Image.Image]) -> NDArray[np.float32]:
        return self._calc_embeddings(
            func=self._process_images_batch,
            inputs=images,
            batch_size=self.image_batch_size,
            desc="CLIP image embeddings",
        )

    def embed_texts(self, texts: List[str]) -> NDArray[np.float32]:
        return self._calc_embeddings(
            func=self._process_texts_batch,
            inputs=texts,
            batch_size=self.text_batch_size,
            desc="CLIP text embeddings",
        )

    def _calc_embeddings(
        self,
        func: Callable[[List[T]], torch.Tensor],
        inputs: List[T],
        batch_size: int,
        desc: str,
    ) -> NDArray[np.float32]:
        embeddings: torch.Tensor = torch.zeros((len(inputs), self.model.projection_dim))
        total = len(inputs) // batch_size + 1
        gen = enumerate(gen_batch(inputs, batch_size))
        for batch_num, batch in tqdm(
            gen, total=total, desc=desc, disable=not self.enable_tqdm
        ):
            with torch.no_grad():
                batch_embeddings = func(batch)
            start_index = batch_num * batch_size
            end_index = (batch_num + 1) * batch_size
            embeddings[start_index:end_index, :] = batch_embeddings
        if self.normalize:
            embeddings /= embeddings.norm(dim=-1, keepdim=True)
        return cast(NDArray[np.float32], embeddings.numpy())

    def _process_images_batch(self, images: List[Image.Image]) -> torch.Tensor:
        inputs: Dict[str, torch.Tensor] = self.processor(
            images=images, return_tensors="pt"
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        return cast(torch.Tensor, self.model.get_image_features(**inputs))

    def _process_texts_batch(self, texts: List[str]) -> torch.Tensor:
        inputs: Dict[str, torch.Tensor] = self.processor(
            text=texts, return_tensors="pt", padding=True
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        return cast(torch.Tensor, self.model.get_text_features(**inputs))
