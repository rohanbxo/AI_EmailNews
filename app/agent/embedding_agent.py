"""Local sentence-embedding wrapper.

Runs `sentence-transformers/all-MiniLM-L6-v2` on CPU. Small (~90MB), fast
(embeds a summary in single-digit ms), and requires no external API. First
call downloads the model to `~/.cache/huggingface/`; subsequent calls hit
the local cache.

Vectors are 384-dim float32 and stored packed via `numpy.tobytes()` in the
`digests.embedding` BYTEA column. Use `unpack()` to get them back.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import List, Optional

import numpy as np


log = logging.getLogger(__name__)

_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_DIM = 384  # dimension of all-MiniLM-L6-v2

_model_lock = threading.Lock()
_model = None


def _get_model():
    """Lazy singleton — avoid loading torch/transformers unless we actually embed."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer  # heavy import

        log.info("Loading embedding model %s (first run downloads ~90MB)...", _MODEL_NAME)
        _model = SentenceTransformer(_MODEL_NAME, device="cpu")
        return _model


def embed(texts: List[str]) -> np.ndarray:
    """Embed a batch of texts. Returns (n, DIM) float32 array, L2-normalized."""
    if not texts:
        return np.zeros((0, _DIM), dtype=np.float32)
    model = _get_model()
    vecs = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,  # so cosine == dot product
    )
    return vecs.astype(np.float32, copy=False)


def embed_one(text: str) -> np.ndarray:
    """Convenience: embed a single string, return a 1-D (DIM,) vector."""
    return embed([text])[0]


def pack(vec: np.ndarray) -> bytes:
    """float32 numpy vector -> raw bytes for BYTEA storage."""
    return np.asarray(vec, dtype=np.float32).tobytes()


def unpack(data: Optional[bytes]) -> Optional[np.ndarray]:
    """BYTEA bytes -> float32 numpy vector; None passes through."""
    if not data:
        return None
    return np.frombuffer(data, dtype=np.float32)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity assuming both vectors are L2-normalized (from `embed`)."""
    return float(np.dot(a, b))
