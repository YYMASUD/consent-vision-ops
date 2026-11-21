"""Polygon zone service: entry/exit/dwell/occupancy logic (spec §6, §11)."""
from __future__ import annotations

import uuid
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
from app.services.zones.geometry import ZoneRuntime, bbox_bottom_center


class ZoneService:
    """Tracks zone membership; generates entry/exit/dwell/occupancy events."""

    def __init__(self) -> None:
        self._zones: dict[uuid.UUID, ZoneRuntime] = {}

    def register_zone(
        self,
        zone_id: uuid.UUID,
        camera_id: uuid.UUID,
        name: str,
        zone_type: str,
        polygon: list[list[float]],
        *,
        max_occupancy: int | None = None,
        dwell_threshold_s: float = 30.0,
    ) -> ZoneRuntime:
        runtime = ZoneRuntime(
            zone_id=zone_id,
            camera_id=camera_id,
            name=name,
            zone_type=zone_type,
            polygon=polygon,
            max_occupancy=max_occupancy,
            dwell_threshold_s=dwell_threshold_s,
        )
        self._zones[zone_id] = runtime
        return runtime

    def zones_for_camera(self, camera_id: uuid.UUID) -> list[ZoneRuntime]:
        return [z for z in self._zones.values() if z.camera_id == camera_id]

    def zone_of_point(self, camera_id: uuid.UUID, point: tuple[float, float]) -> ZoneRuntime | None:
        for zone in self.zones_for_camera(camera_id):
            if zone.contains(point):
                return zone
        return None

    def update_track_position(
        self, track_id: uuid.UUID, camera_id: uuid.UUID, bbox: dict, *, now: datetime | None = None
    ) -> list[dict]:
        """Update membership for one track; return generated events."""
        now = now or utcnow()
        events: list[dict] = []
        current = self.zone_of_point(camera_id, bbox_bottom_center(bbox))

        for zone in self.zones_for_camera(camera_id):
            was_inside = track_id in zone.track_entered_at
            is_inside = current is not None and current.zone_id == zone.zone_id

            if is_inside and not was_inside:
                zone.track_entered_at[track_id] = now
                zone.occupancy += 1
                events.append(self._event(EVT_ZONE_ENTERED, zone, track_id, now))
                if zone.zone_type == ZONE_RESTRICTED:
                    events.append(
                        self._event(EVT_RESTRICTED_ENTRY, zone, track_id, now, severity="high")
                    )
                if zone.zone_type == ZONE_SERVICE:
                    events.append(self._event(EVT_QUEUE_ENTERED, zone, track_id, now))
                if zone.max_occupancy is not None and zone.occupancy > zone.max_occupancy:
                    events.append(
                        self._event(
                            EVT_OCCUPANCY_EXCEEDED,
                            zone,
                            track_id,
                            now,
                            severity="high",
                            details={"occupancy": zone.occupancy, "max": zone.max_occupancy},
                        )
                    )
            elif not is_inside and was_inside:
                entered_at = zone.track_entered_at.pop(track_id, now)
                zone.dwell_alerted.discard(track_id)
                zone.occupancy = max(0, zone.occupancy - 1)
                dwell_s = (now - entered_at).total_seconds()
                events.append(
                    self._event(
                        EVT_ZONE_EXITED, zone, track_id, now, details={"dwell_seconds": dwell_s}
                    )
                )
                if zone.zone_type == ZONE_SERVICE:
                    events.append(self._event(EVT_QUEUE_EXITED, zone, track_id, now))
            elif is_inside and was_inside:
                dwell_s = (now - zone.track_entered_at[track_id]).total_seconds()
                if dwell_s >= zone.dwell_threshold_s and track_id not in zone.dwell_alerted:
                    zone.dwell_alerted.add(track_id)
                    events.append(
                        self._event(
                            EVT_DWELL_REACHED,
                            zone,
                            track_id,
                            now,
                            severity="medium" if zone.zone_type != ZONE_RESTRICTED else "high",
                            details={"dwell_seconds": dwell_s},
                        )
                    )
        return events

    def remove_track(self, track_id: uuid.UUID, *, now: datetime | None = None) -> list[dict]:
        """Track disappeared: exit every zone it was in."""
        now = now or utcnow()
        events: list[dict] = []
        for zone in self._zones.values():
            if track_id in zone.track_entered_at:
                zone.track_entered_at.pop(track_id, None)
                zone.dwell_alerted.discard(track_id)
                zone.occupancy = max(0, zone.occupancy - 1)
                events.append(self._event(EVT_ZONE_EXITED, zone, track_id, now))
        return events

    def occupancy_snapshot(self, camera_id: uuid.UUID | None = None) -> list[dict]:
        zones = self._zones.values() if camera_id is None else self.zones_for_camera(camera_id)
        return [
            {
                "zone_id": str(z.zone_id),
                "camera_id": str(z.camera_id),
                "name": z.name,
                "zone_type": z.zone_type,
                "occupancy": z.occupancy,
                "max_occupancy": z.max_occupancy,
            }
            for z in zones
        ]

    def queue_metrics(self, camera_id: uuid.UUID) -> dict:
        """Queue length and estimated wait across service zones (spec §11)."""
        queue_count = 0
        total_dwell = 0.0
        now = utcnow()
        for zone in self.zones_for_camera(camera_id):
            if zone.zone_type == ZONE_SERVICE:
                queue_count += len(zone.track_entered_at)
                for entered_at in zone.track_entered_at.values():
                    total_dwell += (now - entered_at).total_seconds()
        avg_wait = total_dwell / queue_count if queue_count else 0.0
        return {"queue_count": queue_count, "estimated_wait_seconds": avg_wait}

    @staticmethod
    def _event(
        event_type: str,
        zone: ZoneRuntime,
        track_id: uuid.UUID,
        now: datetime,
        *,
        severity: str = "info",
        details: dict | None = None,
    ) -> dict:
        return {
            "type": event_type,
            "zone_id": str(zone.zone_id),
            "camera_id": str(zone.camera_id),
            "track_id": str(track_id),
            "timestamp": now.isoformat(),
            "severity": severity,
            "details": details or {},
        }
