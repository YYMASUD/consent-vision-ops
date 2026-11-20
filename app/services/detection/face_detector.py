"""Face detection service (spec §6): MediaPipe when available, Haar fallback."""
from __future__ import annotations

from datetime import datetime

import numpy as np

from app.common.utils import utcnow
from app.config.settings import get_settings
from app.observability.metrics import face_detection_total
from app.services.detection.person_detector import Detection


class FaceDetectionService:
    """Detects faces and associates them with containing person boxes (spec §6)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._mp = None
        self._attempted = False

    def _load_mediapipe(self):
        if self._attempted:
            return self._mp
        self._attempted = True
        try:
            import mediapipe as mp  # type: ignore

            self._mp = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=self.settings.face_min_confidence
            )
        except Exception:
            self._mp = None
        return self._mp

    def detect(
        self,
        frame: np.ndarray,
        camera_id: str,
        frame_number: int,
        person_boxes: list[dict] | None = None,
    ) -> list[Detection]:
        now = utcnow()
        detections: list[Detection] = []
        mp = self._load_mediapipe()
        hf, wf = frame.shape[:2]
        if mp is not None:
            try:
                import cv2

                result = mp.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if result and result.detections:
                    for det in result.detections:
                        bb = det.location_data.relative_bounding_box
                        detections.append(
                            Detection(
                                kind="face",
                                bbox={
                                    "x": float(bb.xmin * wf),
                                    "y": float(bb.ymin * hf),
                                    "w": float(bb.width * wf),
                                    "h": float(bb.height * hf),
                                },
                                confidence=float(det.score[0]),
                                frame_number=frame_number,
                                timestamp=now,
                                camera_id=camera_id,
                            )
                        )
            except Exception:
                detections = []
        if not detections:
            detections = self._haar_fallback(frame, camera_id, frame_number, now)
        if person_boxes:
            self._associate(detections, person_boxes)
        face_detection_total.labels(camera_id=camera_id).inc(len(detections))
        return detections

    def _haar_fallback(
        self, frame: np.ndarray, camera_id: str, frame_number: int, now: datetime
    ) -> list[Detection]:
        """OpenCV Haar cascade fallback (ships with opencv-python)."""
        import os

        import cv2

        cascade_path = os.path.join(
            os.path.dirname(cv2.__file__), "data", "haarcascade_frontalface_default.xml"
        )
        if not os.path.exists(cascade_path):
            return []
        cascade = cv2.CascadeClassifier(cascade_path)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
        return [
            Detection(
                kind="face",
                bbox={"x": float(x), "y": float(y), "w": float(w), "h": float(h)},
                confidence=0.60,
                frame_number=frame_number,
                timestamp=now,
                camera_id=camera_id,
            )
            for (x, y, w, h) in faces
        ]

    @staticmethod
    def _associate(faces: list[Detection], person_boxes: list[dict]) -> None:
        """Associate each face with the smallest containing person box (spec §6)."""
        for face in faces:
            fx = face.bbox["x"] + face.bbox["w"] / 2.0
            fy = face.bbox["y"] + face.bbox["h"] / 2.0
            best_idx: int | None = None
            best_area = float("inf")
            for idx, pb in enumerate(person_boxes):
                if pb["x"] <= fx <= pb["x"] + pb["w"] and pb["y"] <= fy <= pb["y"] + pb["h"]:
                    area = pb["w"] * pb["h"]
                    if area < best_area:
                        best_area = area
                        best_idx = idx
            face.person_index = best_idx