"""Prometheus metrics registry (spec §19)."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# --- Detection / recognition quality ------------------------------------------------
person_detection_total = Counter(
    "cvo_person_detection_total", "Person detections", ["camera_id"]
)
face_detection_total = Counter("cvo_face_detection_total", "Face detections", ["camera_id"])
quality_pass_total = Counter("cvo_quality_pass_total", "Face quality passes")
quality_fail_total = Counter("cvo_quality_fail_total", "Face quality rejections", ["reason"])
liveness_total = Counter("cvo_liveness_total", "Liveness decisions", ["decision"])
recognition_total = Counter("cvo_recognition_total", "Recognition decisions", ["decision"])
track_fragmentation_total = Counter("cvo_track_fragmentation_total", "Track fragmentations")
id_switch_total = Counter("cvo_id_switch_total", "Track ID switches")

# --- Camera / stream ----------------------------------------------------------------
camera_fps = Gauge("cvo_camera_fps", "Camera frames per second", ["camera_id"])
camera_offline = Gauge("cvo_camera_offline", "Camera offline (1/0)", ["camera_id"])
stream_reconnect_total = Counter("cvo_stream_reconnect_total", "Stream reconnects", ["camera_id"])
frame_decode_error_total = Counter("cvo_frame_decode_error_total", "Frame decode errors", ["camera_id"])
queue_depth = Gauge("cvo_queue_depth", "Worker queue depth", ["queue"])
dropped_frame_total = Counter("cvo_dropped_frame_total", "Dropped frames", ["camera_id"])

# --- Latency ------------------------------------------------------------------------
inference_latency_ms = Histogram(
    "cvo_inference_latency_ms",
    "Inference latency (ms)",
    ["stage"],
    buckets=(5, 10, 25, 50, 100, 200, 350, 500, 750, 1000, 2000),
)
end_to_end_latency_ms = Histogram(
    "cvo_end_to_end_latency_ms",
    "End-to-end frame latency (ms)",
    buckets=(10, 25, 50, 100, 200, 350, 500, 750, 1000, 2000),
)

# --- Resource / infra ---------------------------------------------------------------
db_latency_ms = Histogram("cvo_db_latency_ms", "DB query latency (ms)", ["op"])
object_storage_failures = Counter("cvo_object_storage_failures_total", "Object storage failures")
retention_job_failures = Counter("cvo_retention_job_failures_total", "Retention job failures")
alerts_raised_total = Counter("cvo_alerts_raised_total", "Alerts raised", ["severity", "type"])
sessions_total = Counter("cvo_sessions_total", "Visit sessions created", ["kind"])


def render_metrics() -> bytes:
    """Render the Prometheus exposition payload."""
    return generate_latest()