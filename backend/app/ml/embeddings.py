"""Embedding providers.

Primary provider: ``sentence-transformers/all-MiniLM-L6-v2`` (384-d, cosine).
Fallback provider: a deterministic signed-hashing lexical embedder (word + bigram + char
n-gram features, sublinear TF, L2 normalised). The fallback is a real, reproducible vector
space — it is not random and not mocked — but it is lexical rather than contextual, so the
similarity thresholds are calibrated per backend.

Vectors are always L2-normalised before storage so cosine similarity is a dot product.
"""

from __future__ import annotations

import hashlib
import logging
import math
import threading
from dataclasses import dataclass

import numpy as np

from app.config.settings import settings
from app.utils.text import content_tokens

logger = logging.getLogger(__name__)

HASHING_DIM = 384


@dataclass(frozen=True)
class EmbeddingInfo:
    model: str
    dim: int
    semantic: bool


class BaseEmbedder:
    info: EmbeddingInfo

    def encode(self, texts: list[str]) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError

    @property
    def model_name(self) -> str:
        return self.info.model

    @property
    def dim(self) -> int:
        return self.info.dim

    @property
    def semantic(self) -> bool:
        return self.info.semantic


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import, lazy on purpose

        self._model = SentenceTransformer(model_name)
        dim = int(self._model.get_sentence_embedding_dimension())
        self.info = EmbeddingInfo(model=model_name, dim=dim, semantic=True)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = self._model.encode(
            texts,
            batch_size=settings.embedding_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


def _signed_hash(feature: str) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8", "ignore"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    index = value % HASHING_DIM
    sign = 1.0 if (value >> 8) & 1 else -1.0
    return index, sign


class HashingEmbedder(BaseEmbedder):
    """Deterministic lexical fallback with word, bigram and character n-gram features."""

    def __init__(self) -> None:
        self.info = EmbeddingInfo(model="hashing-lexical-v1", dim=HASHING_DIM, semantic=False)

    def encode(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), HASHING_DIM), dtype=np.float32)
        for row, text in enumerate(texts):
            vector = self._vectorise(text)
            matrix[row] = vector
        return matrix

    def _vectorise(self, text: str) -> np.ndarray:
        tokens = content_tokens(text)
        if not tokens:
            return np.zeros(HASHING_DIM, dtype=np.float32)
        features: dict[str, float] = {}
        for token in tokens:
            features[f"w:{token}"] = features.get(f"w:{token}", 0.0) + 1.0
        for left, right in zip(tokens, tokens[1:]):
            key = f"b:{left}_{right}"
            features[key] = features.get(key, 0.0) + 0.7
        for token in tokens:
            padded = f"#{token}#"
            for n in (3, 4):
                for start in range(max(0, len(padded) - n + 1)):
                    key = f"c:{padded[start:start + n]}"
                    features[key] = features.get(key, 0.0) + 0.25
        vector = np.zeros(HASHING_DIM, dtype=np.float32)
        for feature, count in features.items():
            index, sign = _signed_hash(feature)
            vector[index] += sign * (1.0 + math.log(count))
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector


class EmbeddingService:
    """Singleton-style accessor that resolves the best available provider once."""

    def __init__(self) -> None:
        self._embedder: BaseEmbedder | None = None
        self._lock = threading.Lock()

    def _resolve(self) -> BaseEmbedder:
        if self._embedder is not None:
            return self._embedder
        with self._lock:
            if self._embedder is not None:
                return self._embedder
            try:
                embedder = SentenceTransformerEmbedder(settings.embedding_model)
                logger.info("Embedding backend: sentence-transformers (%s, %sd)", embedder.model_name, embedder.dim)
            except Exception as exc:
                if not settings.allow_embedding_fallback:
                    raise
                logger.warning(
                    "Sentence-transformers unavailable (%s: %s). Falling back to deterministic lexical "
                    "embeddings. Install torch + sentence-transformers and pre-download the model for "
                    "semantic matching.",
                    type(exc).__name__,
                    exc,
                )
                embedder = HashingEmbedder()
            self._embedder = embedder
            return embedder

    @property
    def embedder(self) -> BaseEmbedder:
        return self._resolve()

    @property
    def info(self) -> EmbeddingInfo:
        return self._resolve().info

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.embedder.dim), dtype=np.float32)
        return self.embedder.encode(texts)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    def warmup(self) -> EmbeddingInfo:
        self.encode_one("warmup")
        return self.info


embedding_service = EmbeddingService()


def pack_vector(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def unpack_vector(blob: bytes | None, dim: int | None) -> np.ndarray | None:
    if not blob:
        return None
    vector = np.frombuffer(blob, dtype=np.float32)
    if dim is not None and vector.shape[0] != dim:
        return None
    return vector


def text_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
