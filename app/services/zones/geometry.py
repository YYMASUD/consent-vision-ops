"""Polygon zone geometry helpers (spec §6, §11)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.common.enums import (
    EVT_DWELL_REACHED,
    EVT_OCCUPANCY_EXCEEDED,
    EVT_QUEUE_ENTERED,
    EVT_QUEUE_EXITED,
    EVT_RESTRICTED_ENTRY,
    EVT_ZONE_ENTERED,
    EVT_ZONE_EXITED,
    ZONE_RESTRICTED,
    ZONE_SERVICE,
)
from app.common.utils import utcnow


def point_in_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i][0], polygon[i][1]
        x2, y2 = polygon[(i + 1) % n][0], polygon[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            x_int = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_int:
                inside = not inside
    return inside


def bbox_center(bbox: dict) -> tuple[float, float]:
    """Center point of an {x, y, w, h} bbox."""
    x = float(bbox.get("x", 0.0))
    y = float(bbox.get("y", 0.0))
    w = float(bbox.get("w", bbox.get("width", 0.0)))
    h = float(bbox.get("h", bbox.get("height", 0.0)))
    return x + w / 2.0, y + h / 2.0


def bbox_bottom_center(bbox: dict) -> tuple[float, float]:
    """Feet position of a bbox (floor-plane zones)."""
    x = float(bbox.get("x", 0.0))
    y = float(bbox.get("y", 0.0))
    w = float(bbox.get("w", bbox.get("width", 0.0)))
    h = float(bbox.get("h", bbox.get("height", 0.0)))
    return x + w / 2.0, y + h


@dataclass
class ZoneRuntime:
    """In-memory runtime state for one zone."""

    zone_id: uuid.UUID
    camera_id: uuid.UUID
    name: str
    zone_type: str
    polygon: list[list[float]]
    max_occupancy: int | None = None
    dwell_threshold_s: float = 30.0
    occupancy: int = 0
    track_entered_at: dict[uuid.UUID, datetime] = field(default_factory=dict)
    dwell_alerted: set[uuid.UUID] = field(default_factory=set)

    def contains(self, point: tuple[float, float]) -> bool:
        return point_in_polygon(point, self.polygon)
