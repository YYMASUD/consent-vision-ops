"""Frame ingestion service (spec §3, §6)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from app.common.enums import EVT_TRACK_UPDATE
from app.common.events import publish
from app.common.utils import utcnow
from app.config.settings import get_settings
from app.services.detection.face_detector import FaceDetectionService
from app.services.detection.person_detector import Detection, PersonDetectionService
from app.services.health.service import CameraHealthService, get_health_service
from app.services.quality.face_quality import FaceQualityService
from app.services.tracking.byte_track import ByteTrackService, Track
from app.services.zones.service import ZoneService


@dataclass
class FrameResult:
    """Result of processing a single camera frame."""

    camera_id: str
    frame_number: int
    timestamp: datetime
    person_detections: list[Detection] = field(default_factory=list)
    face_detections: list[Detection] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)
    zone_events: list[dict] = field(default_factory=list)
    occupancy: int = 0


class IngestionService:
    """Orchestrates the full frame processing pipeline (spec §3, §6)."""

    def __init__(
        self,
        person_detector: PersonDetectionService | None = None,
        face_detector: FaceDetectionService | None = None,
        face_quality: FaceQualityService | None = None,
        tracker: ByteTrackService | None = None,
        zone_service: ZoneService | None = None,
        health_service: CameraHealthService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.person_detector = person_detector or PersonDetectionService()
        self.face_detector = face_detector or FaceDetectionService()
        self.face_quality = face_quality or FaceQualityService()
        self.tracker = tracker or ByteTrackService()
        self.zone_service = zone_service or ZoneService()
        self.health_service = health_service or get_health_service()

    def _decode_frame(self, frame_bytes: bytes) -> np.ndarray | None:
        """Decode JPEG/PNG bytes to a numpy BGR array via OpenCV."""
        import cv2

        buf = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return frame  # None if decode fails

    async def process_frame(
        self,
        camera_id: str,
        frame_bytes: bytes,
        frame_number: int,
        now: datetime | None = None,
    ) -> FrameResult:
        """Full ingestion pipeline for one frame (spec §3, §6)."""
        now = now or utcnow()
        settings = self.settings

        # Always run health check first (even on skipped frames)
        health_result = await self.health_check(camera_id, frame_bytes, frame_number, now)

        # Frame stride / skipping
        if frame_number % settings.frame_stride != 0:
            return FrameResult(
                camera_id=camera_id,
                frame_number=frame_number,
                timestamp=now,
            )

        # Decode frame
        frame = self._decode_frame(frame_bytes)
        if frame is None:
            return FrameResult(
                camera_id=camera_id,
                frame_number=frame_number,
                timestamp=now,
            )

        # 1. Person detection
        person_detections = self.person_detector.detect(frame, camera_id, frame_number)

        # 2. Face detection (with person box context)
        person_boxes = [d.bbox for d in person_detections]
        face_detections = self.face_detector.detect(
            frame, camera_id, frame_number, person_boxes=person_boxes
        )

        # 3. Face quality evaluation per face
        for face_det in face_detections:
            quality = self.face_quality.evaluate(
                frame,
                face_det.bbox,
                pose=face_det.pose,
                landmarks=face_det.landmarks,
                detection_confidence=face_det.confidence,
            )
            face_det.alignment = quality  # store quality result on detection

        # 4. Tracker update — convert detections to dict list
        detection_dicts = [
            {
                "bbox": d.bbox,
                "confidence": d.confidence,
                "person_index": d.person_index,
            }
            for d in person_detections
        ]
        tracks = self.tracker.update(
            camera_id, detection_dicts, frame_number=frame_number, now=now
        )

        # 5. Zone events from track positions
        zone_events: list[dict] = []
        for track in tracks:
            if track.bbox:
                events = self.zone_service.update_track_position(
                    track.track_id, uuid.UUID(track.camera_id) if isinstance(track.camera_id, str) else track.camera_id,
                    track.bbox,
                    now=now,
                )
                zone_events.extend(events)

        # 6. Occupancy count from active tracks
        occupancy = len([t for t in self.tracker.active_tracks(camera_id)])

        # 7. Publish EVT_TRACK_UPDATE
        await publish(
            EVT_TRACK_UPDATE,
            {
                "camera_id": camera_id,
                "frame_number": frame_number,
                "timestamp": now.isoformat(),
                "tracks": [t.to_dict() for t in tracks],
                "occupancy": occupancy,
                "zone_events": zone_events,
            },
        )

        return FrameResult(
            camera_id=camera_id,
            frame_number=frame_number,
            timestamp=now,
            person_detections=person_detections,
            face_detections=face_detections,
            tracks=tracks,
            zone_events=zone_events,
            occupancy=occupancy,
        )

    async def health_check(
        self,
        camera_id: str,
        frame_bytes: bytes,
        frame_number: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Check frame health (frozen/black/white/obstruction).

        Returns dict with status, event_type or None, metrics.
        """
        now = now or utcnow()
        result = self.health_service.check_frame(camera_id, frame_bytes, frame_number, now=now)
        return result


# --- Module-level singleton ---------------------------------------------------

_ingestion_service: IngestionService | None = None


def get_ingestion_service() -> IngestionService:
    """Return (or lazily create) the module-level IngestionService singleton."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
