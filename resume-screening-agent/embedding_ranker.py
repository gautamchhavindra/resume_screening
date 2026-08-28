"""Embedding generation + cosine similarity ranking (no LLM calls)."""

from __future__ import annotations

import logging
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import AppConfig
from resume_parser import ParsedResume

# Windows without Developer Mode/admin can't create the symlinks the HF Hub
# cache uses by default; this makes it copy files instead (avoids a
# WinError-1314 retry-and-fallback delay on first model download).
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return an (n, dim) array of embeddings for the given texts."""


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embeddings via fastembed (ONNX runtime) — no torch dependency,
    much lower memory footprint than sentence-transformers."""

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        logger.info("Loading local embedding model (fastembed/onnxruntime): %s", model_name)
        self._model = TextEmbedding(model_name=model_name)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return np.asarray(list(self._model.embed(texts)))


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str, api_key: str | None):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai embedding provider")
        from langchain_openai import OpenAIEmbeddings

        self._embeddings = OpenAIEmbeddings(model=model_name, api_key=api_key)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._embeddings.embed_documents(texts))


@lru_cache(maxsize=4)
def _cached_provider(provider_type: str, model_name: str, api_key: str | None) -> EmbeddingProvider:
    # Loading the model (esp. LocalEmbeddingProvider's ONNX weights) is the
    # expensive part — cache the provider instance per process so repeated
    # requests reuse it instead of reloading the model every time.
    if provider_type == "openai":
        return OpenAIEmbeddingProvider(model_name, api_key)
    return LocalEmbeddingProvider(model_name)


def get_embedding_provider(config: AppConfig) -> EmbeddingProvider:
    if config.embedding_provider == "openai":
        return _cached_provider("openai", config.openai_embedding_model, config.openai_api_key)
    return _cached_provider("local", config.local_embedding_model, None)


@dataclass
class RankedResume:
    resume: ParsedResume
    similarity: float


def rank_resumes(
    jd_text: str, resumes: list[ParsedResume], provider: EmbeddingProvider
) -> list[RankedResume]:
    if not resumes:
        return []

    jd_vector = provider.embed_texts([jd_text])
    resume_vectors = provider.embed_texts([r.text for r in resumes])

    similarities = cosine_similarity(jd_vector, resume_vectors)[0]

    ranked = [
        RankedResume(resume=resume, similarity=float(score))
        for resume, score in zip(resumes, similarities)
    ]
    ranked.sort(key=lambda r: r.similarity, reverse=True)
    return ranked


def select_shortlist(
    ranked: list[RankedResume], top_percent: float, min_candidates: int
) -> list[RankedResume]:
    if not ranked:
        return []
    count = max(min_candidates, math.ceil(len(ranked) * top_percent / 100))
    count = min(count, len(ranked))
    return ranked[:count]
