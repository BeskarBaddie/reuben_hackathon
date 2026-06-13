"""Local text embeddings via Ollama for dense retrieval and grounding checks.

Embeddings are produced by a local Ollama embedding model (default
``nomic-embed-text``) through the ``/api/embed`` endpoint. Vectors are
L2-normalised so cosine similarity reduces to a dot product.

Every entry point fails soft: if Ollama is unreachable or the model is missing,
the functions return ``None`` and callers fall back to lexical (BM25) retrieval,
so the system still runs fully offline.
"""

from __future__ import annotations

import httpx
import numpy as np

from app.core.config import settings


def embedding_model() -> str:
    return settings.ollama_embedding_model


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def embed_texts(texts: list[str], timeout: float = 120.0) -> np.ndarray | None:
    """Embed a batch of texts. Returns an (n, dim) float32 array or None on failure."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    try:
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/embed",
            json={"model": embedding_model(), "input": texts},
            timeout=timeout,
        )
        response.raise_for_status()
        vectors = response.json().get("embeddings")
        if not vectors or len(vectors) != len(texts):
            return None
        return _normalise(np.asarray(vectors, dtype=np.float32))
    except Exception:
        return None


def embed_text(text: str, timeout: float = 60.0) -> np.ndarray | None:
    """Embed a single text. Returns a (dim,) float32 vector or None on failure."""
    result = embed_texts([text], timeout=timeout)
    if result is None or result.shape[0] == 0:
        return None
    return result[0]


def cosine_scores(query_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity of a (normalised) query vector against (normalised) rows."""
    if matrix.size == 0:
        return np.zeros((0,), dtype=np.float32)
    return matrix @ query_vector


def max_cosine(query_vector: np.ndarray, matrix: np.ndarray) -> float:
    scores = cosine_scores(query_vector, matrix)
    return float(scores.max()) if scores.size else 0.0
