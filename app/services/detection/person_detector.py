"""Person detection service (spec §6): YOLO when available, deterministic fallback."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.common.utils import utcnow
from app.config.settings import get_settings
from app.observability.metrics import person_detection_total


@dataclass
class Detection:
    """Normalized detection output shared by person and face detectors."""

    kind: str  # person | face
    bbox: dict  # {x, y, w, h} pixels
    confidence: float
    frame_number: int
    timestamp: datetime
    camera_id: str
    landmarks: list[list[float]] | None = None
    pose: dict | None = None  # {yaw, pitch, roll} degrees
    alignment: dict | None = None
    person_index: int | None = None


class PersonDetectionService:
    """YOLO person detection with a deterministic image-processing fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._model = None
        self._attempted = False

    def _load_model(self):
        """Load local YOLO weights only (no runtime downloads); else fallback."""
        if self._attempted:
            return self._model
        self._attempted = True
        try:
            import os

            from ultralytics import YOLO  # type: ignore

            local = os.path.join(self.settings.model_dir, "yolov8n.pt")
            self._model = YOLO(local) if os.path.exists(local) else None
        except Exception:
            self._model = None
        return self._model

    def detect(self, frame: np.ndarray, camera_id: str, frame_number: int) -> list[Detection]:
        now = utcnow()
        detections: list[Detection] = []
        model = self._load_model()
        if model is not None:
            try:
                for result in model.predict(frame, verbose=False, classes=[0], conf=0.35):
                    for box in getattr(result, "boxes", []):
                        x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                        detections.append(
                            Detection(
                                kind="person",
                                bbox={"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1},
                                confidence=float(box.conf.item()),
                                frame_number=frame_number,
                                timestamp=now,
                                camera_id=camera_id,
                            )
                        )
            except Exception:
                detections = []
        if not detections:
            detections = self._fallback(frame, camera_id, frame_number, now)
        person_detection_total.labels(camera_id=camera_id).inc(len(detections))
        return detections

    def _fallback(
        self, frame: np.ndarray, camera_id: str, frame_number: int, now: datetime
    ) -> list[Detection]:
        """Foreground-blob person candidates without ML weights (CPU-only mode)."""
        import cv2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hf, wf = gray.shape[:2]
        out: list[Detection] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w >= wf * 0.06 and h >= hf * 0.12 and h >= w * 0.8:
                out.append(
                    Detection(
                        kind="person",
                        bbox={"x": float(x), "y": float(y), "w": float(w), "h": float(h)},
                        confidence=0.50,
                        frame_number=frame_number,
                        timestamp=now,
                        camera_id=camera_id,
                    )
                )
        return out[:12]
