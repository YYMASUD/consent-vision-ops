"""Embedding generation (spec §9, §20): ArcFace when available, deterministic fallback."""
from __future__ import annotations

import numpy as np

from app.config.settings import get_settings

MODEL_VERSION = "hashing-v1"
EMBED_DIM = 512


class EmbeddingService:
    """Generates L2-normalized face embeddings from aligned crops."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._arcface = None
        self._attempted = False

    def _load_arcface(self):
        """Load InsightFace ArcFace only if the package and weights exist locally."""
        if self._attempted:
            return self._arcface
        self._attempted = True
        try:
            from insightface.app import FaceAnalysis  # type: ignore

            app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=0, det_size=(320, 320))
            self._arcface = app
        except Exception:
            self._arcface = None
        return self._arcface

    def embed(self, crop: np.ndarray | None) -> list[float] | None:
        """Return a 512-dim L2-normalized embedding, or None when no crop."""
        if crop is None or crop.size == 0:
            return None
        model = self._load_arcface()
        if model is not None:
            try:
                faces = model.get(crop[:, :, ::-1])
                if faces:
                    vec = faces[0].normed_embedding.astype(float).tolist()
                    return vec
            except Exception:
                pass
        return self._perceptual_embed(crop)

    def _perceptual_embed(self, crop: np.ndarray) -> list[float]:
        """Deterministic perceptual embedding (16x16 gray + gradient histogram)."""
        import cv2

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (16, 16)).astype(np.float32) / 255.0
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy)
        hist, _ = np.histogram(ang, bins=16, range=(0.0, 2.0 * np.pi), weights=mag)
        hist = hist.astype(np.float32)
        hist = hist / (np.linalg.norm(hist) + 1e-6)
        base = small.flatten()
        base = base / (np.linalg.norm(base) + 1e-6)
        reps = EMBED_DIM - base.size - hist.size
        tiled = np.tile(np.concatenate([base, hist]), int(np.ceil(reps / (base.size + hist.size))))
        vec = np.concatenate([base, hist, tiled[:reps]]).astype(np.float32)
        norm = float(np.linalg.norm(vec)) or 1.0
        return (vec / norm).tolist()

    @property
    def model_version(self) -> str:
        return "arcface-v1" if self._arcface is not None else MODEL_VERSION
