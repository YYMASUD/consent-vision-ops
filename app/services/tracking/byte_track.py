"""ByteTrack-style tracking service (spec §6).

Temporary track_id scoped to a camera stream; states active / temporarily_lost /
exited / closed; velocity, direction, zone membership, first/last seen; re-ID after
short occlusions; ID-switch and fragmentation counters.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.common.enums import TRACK_ACTIVE, TRACK_CLOSED, TRACK_EXITED, TRACK_LOST
from app.common.utils import new_id, utcnow
from app.observability.metrics import id_switch_total, track_fragmentation_total


def iou(a: dict, b: dict) -> float:
    """Intersection-over-union of two {x, y, w, h} boxes."""
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix = max(0.0, min(ax2, bx2) - max(a["x"], b["x"]))
    iy = max(0.0, min(ay2, by2) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


def center_of(bbox: dict) -> tuple[float, float]:
    return bbox["x"] + bbox["w"] / 2.0, bbox["y"] + bbox["h"] / 2.0


def direction_of(velocity: tuple[float, float]) -> str:
    vx, vy = velocity
    if abs(vx) < 5.0 and abs(vy) < 5.0:
        return "static"
    if abs(vx) >= abs(vy):
        return "right" if vx > 0 else "left"
    return "down" if vy > 0 else "up"


@dataclass
class Track:
    """One tracked person on one camera stream (temporary, non-persistent)."""

    track_id: uuid.UUID
    camera_id: str
    state: str = TRACK_ACTIVE
    bbox: dict = field(default_factory=dict)
    confidence: float = 0.0
    hits: int = 0
    age: int = 0
    time_since_update: int = 0
    velocity: tuple[float, float] = (0.0, 0.0)
    direction: str = "static"
    zone_id: uuid.UUID | None = None
    first_seen_at: datetime = field(default_factory=utcnow)
    last_seen_at: datetime = field(default_factory=utcnow)
    person_index: int | None = None

    def to_dict(self) -> dict:
        return {
            "track_id": str(self.track_id),
            "camera_id": self.camera_id,
            "state": self.state,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "velocity": list(self.velocity),
            "direction": self.direction,
            "zone_id": str(self.zone_id) if self.zone_id else None,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
        }


class ByteTrackService:
    """Greedy IoU tracker with low-score rescue (ByteTrack-style two stages)."""

    def __init__(self, *, iou_threshold: float = 0.3, lost_patience: int = 8, exit_patience: int = 30):
        self.iou_threshold = iou_threshold
        self.lost_patience = lost_patience
        self.exit_patience = exit_patience
        self._tracks: dict[str, list[Track]] = {}

    def tracks_for_camera(self, camera_id: str) -> list[Track]:
        return [t for t in self._tracks.get(camera_id, []) if t.state != TRACK_CLOSED]

    def active_tracks(self, camera_id: str) -> list[Track]:
        return [t for t in self.tracks_for_camera(camera_id) if t.state == TRACK_ACTIVE]

    def live_tracks_payload(self, camera_id: str | None = None) -> list[dict]:
        cameras = [camera_id] if camera_id else list(self._tracks)
        return [t.to_dict() for cam in cameras for t in self.tracks_for_camera(cam)]

    def update(
        self, camera_id: str, detections: list[dict], *, frame_number: int = 0, now: datetime | None = None
    ) -> list[Track]:
        """Associate detections to existing tracks; create/lose/exit as needed."""
        now = now or utcnow()
        cam_tracks = self._tracks.setdefault(camera_id, [])
        candidates = [t for t in cam_tracks if t.state in (TRACK_ACTIVE, TRACK_LOST)]
        matched: list[tuple[Track, dict]] = []
        used: set[int] = set()

        # stage 1: association with best-IoU candidate
        for track in candidates:
            best_iou, best_idx = 0.0, None
            for idx, det in enumerate(detections):
                if idx in used:
                    continue
                score = iou(track.bbox, det["bbox"]) if track.bbox and det.get("bbox") else 0.0
                if score > best_iou:
                    best_iou, best_idx = score, idx
            if best_idx is not None and best_iou >= self.iou_threshold:
                matched.append((track, detections[best_idx]))
                used.add(best_idx)

        # stage 2: rescue unmatched detections onto nearby un-matched tracks
        matched_ids = {id(t) for t, _ in matched}
        for idx, det in enumerate(detections):
            if idx in used:
                continue
            for track in candidates:
                if id(track) in matched_ids:
                    continue
                if track.bbox and det.get("bbox") and iou(track.bbox, det["bbox"]) > 0.1:
                    matched.append((track, det))
                    used.add(idx)
                    matched_ids.add(id(track))
                    break

        # apply matches (velocity, direction, id-switch detection)
        for track, det in matched:
            if track.person_index is not None and det.get("person_index") is not None:
                if track.person_index != det["person_index"]:
                    id_switch_total.inc()
            prev = center_of(track.bbox) if track.bbox else center_of(det["bbox"])
            cur = center_of(det["bbox"])
            dt = max((now - track.last_seen_at).total_seconds(), 1e-6)
            track.velocity = ((cur[0] - prev[0]) / dt, (cur[1] - prev[1]) / dt)
            track.direction = direction_of(track.velocity)
            track.bbox = det["bbox"]
            track.confidence = float(det.get("confidence", 0.0))
            track.person_index = det.get("person_index")
            track.hits += 1
            track.age += 1
            track.time_since_update = 0
            track.state = TRACK_ACTIVE
            track.last_seen_at = now

        # age out unmatched tracks: active -> lost -> exited -> closed
        for track in candidates:
            if id(track) in matched_ids:
                continue
            track.time_since_update += 1
            if track.state == TRACK_ACTIVE and track.time_since_update > 2:
                track.state = TRACK_LOST
            if track.time_since_update > self.lost_patience:
                track.state = TRACK_EXITED
            if track.time_since_update > self.exit_patience:
                track.state = TRACK_CLOSED

        # new temporary tracks for unmatched detections
        for idx, det in enumerate(detections):
            if idx in used:
                continue
            cam_tracks.append(
                Track(
                    track_id=new_id(),
                    camera_id=camera_id,
                    bbox=det["bbox"],
                    confidence=float(det.get("confidence", 0.0)),
                    person_index=det.get("person_index"),
                    hits=1,
                    age=1,
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )

        # fragmentation metric: exited track overlapping a live one
        frag = sum(
            1
            for t in cam_tracks
            if t.state == TRACK_EXITED
            and t.bbox
            and any(
                o is not t and o.state in (TRACK_ACTIVE, TRACK_LOST) and o.bbox and iou(t.bbox, o.bbox) > 0.5
                for o in cam_tracks
            )
        )
        if frag:
            track_fragmentation_total.inc(frag)
        return [t for t, _ in matched]

    def reap(self, camera_id: str | None = None) -> int:
        """Close exited tracks older than 5 minutes."""
        count = 0
        for cam in [camera_id] if camera_id else list(self._tracks):
            for track in self._tracks.get(cam, []):
                if track.state == TRACK_EXITED and utcnow() - track.last_seen_at > timedelta(minutes=5):
                    track.state = TRACK_CLOSED
                    count += 1
        return count

