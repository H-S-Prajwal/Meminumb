from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Interface all embedders must satisfy."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return a fixed-length embedding vector for the given text."""


class DummyEmbedder(BaseEmbedder):
    """
    Deterministic embedder for tests and offline demos.

    No external dependencies. Produces a reproducible 64-dim vector from
    an MD5 hash of the text — not semantically meaningful, but good enough
    to exercise the full memory pipeline without any API calls.
    """

    DIM = 64

    def embed(self, text: str) -> list[float]:
        digest = hashlib.md5(text.encode()).digest()
        # Tile the 16-byte digest to fill DIM floats in [0, 1]
        values = []
        for i in range(self.DIM):
            values.append(digest[i % 16] / 255.0)
        return values


class LocalEmbedder(BaseEmbedder):
    """
    Embedder backed by sentence-transformers (runs fully offline).

    Install: pip install meminumb[local]
    Default model: all-MiniLM-L6-v2 (384 dims, ~90 MB, fast on CPU)
    """

    def __init__(self, model: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "LocalEmbedder requires sentence-transformers. "
                "Install it with:  pip install meminumb[local]"
            ) from exc
        self._model = SentenceTransformer(model)

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()


class OpenAIEmbedder(BaseEmbedder):
    """
    Embedder backed by the OpenAI Embeddings API.

    Install: pip install meminumb[openai]
    Requires OPENAI_API_KEY environment variable (or pass api_key=).
    Default model: text-embedding-3-small (1536 dims)
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "OpenAIEmbedder requires the openai package. "
                "Install it with:  pip install meminumb[openai]"
            ) from exc
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(input=text, model=self._model)
        return response.data[0].embedding
