"""Face quality evaluation (spec §7).

Checks: detection confidence, face width, blur (Laplacian), lighting, pose,
occlusion, resolution, motion, frame integrity. Blocks embedding generation
when any hard requirement fails.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from app.config.settings import get_settings
from app.observability.metrics import quality_fail_total, quality_pass_total


class FaceQualityService:
    """Scores face crops; returns the spec §7 JSON contract."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def evaluate(
        self,
        frame: np.ndarray,
        bbox: dict,
        *,
        pose: dict | None = None,
        landmarks: list[list[float]] | None = None,
        detection_confidence: float = 1.0,
        motion_score: float | None = None,
    ) -> dict[str, Any]:
        import cv2

        s = self.settings
        reasons: list[str] = []
        x, y = int(bbox["x"]), int(bbox["y"])
        w, h = int(bbox["w"]), int(bbox["h"])
        hf, wf = frame.shape[:2]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(wf, x + w), min(hf, y + h)
        crop = frame[y0:y1, x0:x1] if x1 > x0 and y1 > y0 else None

        conf_score = float(detection_confidence)
        if conf_score < s.face_min_confidence:
            reasons.append("face_detection_confidence_below_threshold")

        face_width = max(0, w)
        size_score = min(1.0, face_width / max(1, s.face_min_width_px))
        if face_width < s.face_min_width_px:
            reasons.append("face_width_below_minimum")

        blur_score = 0.0
        if crop is not None and crop.size:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            blur_score = min(1.0, laplacian_var / (s.face_blur_laplacian_threshold * 4.0))
            if laplacian_var < s.face_blur_laplacian_threshold:
                reasons.append("blur_above_threshold")
        else:
            reasons.append("empty_or_invalid_face_crop")

        light_score = 0.0
        if crop is not None and crop.size:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(gray.mean())
            if mean_brightness < 40.0:
                light_score = mean_brightness / 40.0
                reasons.append("underexposed")
            elif mean_brightness > 220.0:
                light_score = (255.0 - mean_brightness) / 35.0
                reasons.append("overexposed")
            else:
                light_score = 1.0

        pose_score = 1.0
        if pose:
            yaw = abs(float(pose.get("yaw", 0.0)))
            pitch = abs(float(pose.get("pitch", 0.0)))
            roll = abs(float(pose.get("roll", 0.0)))
            yaw_score = max(0.0, 1.0 - yaw / max(s.face_max_yaw_deg, 1.0))
            pitch_score = max(0.0, 1.0 - pitch / max(s.face_max_pitch_deg, 1.0))
            roll_score = max(0.0, 1.0 - roll / max(s.face_max_roll_deg, 1.0))
            pose_score = (yaw_score + pitch_score + roll_score) / 3.0
            if yaw > s.face_max_yaw_deg:
                reasons.append("yaw_exceeds_limit")
            if pitch > s.face_max_pitch_deg:
                reasons.append("pitch_exceeds_limit")
            if roll > s.face_max_roll_deg:
                reasons.append("roll_exceeds_limit")

        occlusion_score = 1.0
        if landmarks:
            pts = np.array(landmarks, dtype=float)
            if pts.size == 0 or np.isnan(pts).any() or (pts == 0).all():
                occlusion_score = 0.0
                reasons.append("landmarks_missing_or_obscured")
            else:
                spread = float(pts.max() - pts.min())
                if spread < 4.0:
                    occlusion_score = 0.0
                    reasons.append("landmarks_missing_or_obscured")

        if motion_score is not None and motion_score > 0.8:
            reasons.append("excessive_motion")

        overall = float(
            np.clip(
                0.35 * blur_score
                + 0.20 * light_score
                + 0.20 * pose_score
                + 0.15 * size_score
                + 0.10 * occlusion_score,
                0.0,
                1.0,
            )
        )
        usable = len(reasons) == 0
        if usable:
            quality_pass_total.inc()
        else:
            for reason in reasons:
                quality_fail_total.labels(reason=reason).inc()
        return {
            "usable": usable,
            "overall_score": round(overall, 4),
            "blur_score": round(blur_score, 4),
            "lighting_score": round(light_score, 4),
            "pose_score": round(pose_score, 4),
            "occlusion_score": round(occlusion_score, 4),
            "face_width_px": face_width,
            "rejection_reasons": reasons,
        }

    def evaluate_simple(
        self,
        frame_gray_variance: float,
        face_width: int,
        brightness: float,
        *,
        detection_confidence: float = 1.0,
        pose: dict | None = None,
    ) -> dict[str, Any]:
        """Dict-based variant for pipelines/tests operating on precomputed stats."""
        s = self.settings
        reasons: list[str] = []
        blur_score = min(1.0, frame_gray_variance / (s.face_blur_laplacian_threshold * 4.0))
        if frame_gray_variance < s.face_blur_laplacian_threshold:
            reasons.append("blur_above_threshold")
        size_score = min(1.0, face_width / max(1, s.face_min_width_px))
        if face_width < s.face_min_width_px:
            reasons.append("face_width_below_minimum")
        if brightness < 40.0:
            reasons.append("underexposed")
        elif brightness > 220.0:
            reasons.append("overexposed")
        light_score = 1.0 if 40.0 <= brightness <= 220.0 else 0.0
        pose_score = 1.0
        if pose:
            for axis, limit in (
                ("yaw", s.face_max_yaw_deg),
                ("pitch", s.face_max_pitch_deg),
                ("roll", s.face_max_roll_deg),
            ):
                if abs(float(pose.get(axis, 0.0))) > limit:
                    reasons.append(f"{axis}_exceeds_limit")
                    pose_score = min(pose_score, 0.5)
        conf_ok = detection_confidence >= s.face_min_confidence
        if not conf_ok:
            reasons.append("face_detection_confidence_below_threshold")
        overall = 0.4 * blur_score + 0.25 * light_score + 0.2 * size_score + 0.15 * pose_score
        overall *= 1.0 if conf_ok else 0.5
        usable = len(reasons) == 0
        if usable:
            quality_pass_total.inc()
        else:
            for reason in reasons:
                quality_fail_total.labels(reason=reason).inc()
        return {
            "usable": usable,
            "overall_score": round(float(np.clip(overall, 0.0, 1.0)), 4),
            "blur_score": round(blur_score, 4),
            "lighting_score": round(light_score, 4),
            "pose_score": round(pose_score, 4),
            "occlusion_score": 1.0,
            "face_width_px": face_width,
            "rejection_reasons": reasons,
        }

