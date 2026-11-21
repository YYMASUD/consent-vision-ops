"""Shared string enums / vocabularies used across services, models, and APIs.

Kept as plain string constants for portability (DB columns store strings).
"""
from __future__ import annotations

# --- Sessions -----------------------------------------------------------------
SESSION_ACTIVE = "active"
SESSION_CLOSED = "closed"
SESSION_STATUSES = (SESSION_ACTIVE, SESSION_CLOSED)

# --- Verification ---------------------------------------------------------------
VERIFICATION_UNVERIFIED = "unverified"
VERIFICATION_PENDING_REVIEW = "pending_review"
VERIFICATION_CONFIRMED = "confirmed"
VERIFICATION_REJECTED = "rejected"
VERIFICATION_CONFLICT = "multi_factor_conflict"
VERIFICATION_STATUSES = (
    VERIFICATION_UNVERIFIED,
    VERIFICATION_PENDING_REVIEW,
    VERIFICATION_CONFIRMED,
    VERIFICATION_REJECTED,
    VERIFICATION_CONFLICT,
)

# --- Recognition decisions --------------------------------------------------------
REC_NO_MATCH = "no_match"
REC_UNCERTAIN = "uncertain_match"
REC_CONFIRMED = "confirmed_match"
REC_BLOCKED_NO_CONSENT = "blocked_no_consent"
REC_BLOCKED_POLICY = "blocked_policy"
REC_BLOCKED_QUALITY = "blocked_quality"
REC_BLOCKED_LIVENESS = "blocked_liveness"
REC_SPOOF_SUSPECTED = "spoof_suspected"
REC_DISABLED = "recognition_disabled"
REC_DECISIONS = (
    REC_NO_MATCH,
    REC_UNCERTAIN,
    REC_CONFIRMED,
    REC_BLOCKED_NO_CONSENT,
    REC_BLOCKED_POLICY,
    REC_BLOCKED_QUALITY,
    REC_BLOCKED_LIVENESS,
    REC_SPOOF_SUSPECTED,
    REC_DISABLED,
)

# --- Liveness -----------------------------------------------------------------
LIVE = "live"
SPOOF_ATTACK = "suspected_presentation_attack"
LIVE_INSUFFICIENT = "insufficient_evidence"
LIVE_UNAVAILABLE = "unavailable"
LIVENESS_DECISIONS = (LIVE, SPOOF_ATTACK, LIVE_INSUFFICIENT, LIVE_UNAVAILABLE)

# --- Access control ---------------------------------------------------------------
CRED_BADGE = "badge"
CRED_QR = "qr"
CRED_NFC = "nfc"
CRED_PIN = "pin"
CRED_TURNSTILE = "turnstile"
CRED_DOOR = "door"
CRED_MANUAL = "manual"
CREDENTIAL_TYPES = (CRED_BADGE, CRED_QR, CRED_NFC, CRED_PIN, CRED_TURNSTILE, CRED_DOOR, CRED_MANUAL)

ACCESS_GRANTED = "granted"
ACCESS_DENIED = "denied"
ACCESS_CONFLICT = "conflict"

# --- Zones ----------------------------------------------------------------------
ZONE_ENTRY = "entry_zone"
ZONE_EXIT = "exit_zone"
ZONE_RESTRICTED = "restricted_zone"
ZONE_WAITING = "waiting_zone"
ZONE_SERVICE = "service_zone"
ZONE_SAFE = "safe_zone"
ZONE_NO_ACCESS = "no_access_zone"
ZONE_TYPES = (
    ZONE_ENTRY,
    ZONE_EXIT,
    ZONE_RESTRICTED,
    ZONE_WAITING,
    ZONE_SERVICE,
    ZONE_SAFE,
    ZONE_NO_ACCESS,
)

# --- Zone / occupancy events -------------------------------------------------------
EVT_ZONE_ENTERED = "zone_entered"
EVT_ZONE_EXITED = "zone_exited"
EVT_DWELL_REACHED = "zone_dwell_threshold_reached"
EVT_RESTRICTED_ENTRY = "restricted_zone_entry"
EVT_QUEUE_ENTERED = "queue_entered"
EVT_QUEUE_EXITED = "queue_exited"
EVT_OCCUPANCY_EXCEEDED = "occupancy_threshold_exceeded"

# --- Tracks ------------------------------------------------------------------------
TRACK_ACTIVE = "active"
TRACK_LOST = "temporarily_lost"
TRACK_EXITED = "exited"
TRACK_CLOSED = "closed"
TRACK_STATES = (TRACK_ACTIVE, TRACK_LOST, TRACK_EXITED, TRACK_CLOSED)


# --- Camera health -------------------------------------------------------------------
CAM_UNKNOWN = "unknown"
CAM_HEALTHY = "healthy"
CAM_DEGRADED = "degraded"
CAM_OFFLINE = "offline"
CAMERA_HEALTH_STATUSES = (CAM_UNKNOWN, CAM_HEALTHY, CAM_DEGRADED, CAM_OFFLINE)

HEALTH_OFFLINE = "camera_offline"
HEALTH_RECONNECT_LOOP = "stream_reconnect_loop"
HEALTH_FROZEN = "frozen_frame"
HEALTH_BLACK = "black_screen"
HEALTH_WHITE = "white_screen"
HEALTH_OBSTRUCTION = "lens_obstruction"
HEALTH_TAMPER = "camera_tamper"
HEALTH_ANGLE_CHANGED = "camera_angle_changed"
HEALTH_LOW_FPS = "low_fps"
HEALTH_PACKET_LOSS = "high_packet_loss"
HEALTH_DECODE_ERRORS = "high_decode_error_rate"
HEALTH_LOW_LIGHT = "persistent_low_light"
HEALTH_MOTION_BLUR = "excessive_motion_blur"
HEALTH_WRITE_FAILURE = "storage_write_failure"
HEALTH_EVENT_TYPES = (
    HEALTH_OFFLINE,
    HEALTH_RECONNECT_LOOP,
    HEALTH_FROZEN,
    HEALTH_BLACK,
    HEALTH_WHITE,
    HEALTH_OBSTRUCTION,
    HEALTH_TAMPER,
    HEALTH_ANGLE_CHANGED,
    HEALTH_LOW_FPS,
    HEALTH_PACKET_LOSS,
    HEALTH_DECODE_ERRORS,
    HEALTH_LOW_LIGHT,
    HEALTH_MOTION_BLUR,
    HEALTH_WRITE_FAILURE,
)

# --- Alerts ---------------------------------------------------------------------------
SEV_INFO = "info"
SEV_LOW = "low"
SEV_MEDIUM = "medium"
SEV_HIGH = "high"
SEV_CRITICAL = "critical"
SEVERITIES = (SEV_INFO, SEV_LOW, SEV_MEDIUM, SEV_HIGH, SEV_CRITICAL)

ALERT_OPEN = "open"
ALERT_ACKNOWLEDGED = "acknowledged"
ALERT_RESOLVED = "resolved"
ALERT_REOPENED = "reopened"
ALERT_STATUSES = (ALERT_OPEN, ALERT_ACKNOWLEDGED, ALERT_RESOLVED, ALERT_REOPENED)

ALERT_UNAUTHORIZED_MATCH = "unauthorized_match"
ALERT_RESTRICTED_ENTRY = "restricted_zone_entry"
ALERT_UNKNOWN_RESTRICTED = "unknown_person_in_restricted_zone"
ALERT_LIVENESS_ATTACK = "liveness_suspected_attack"
ALERT_MFA_CONFLICT = "multi_factor_conflict"
ALERT_CAMERA_OFFLINE = "camera_offline"
ALERT_CAMERA_TAMPER = "camera_tamper"
ALERT_OCCUPANCY_EXCEEDED = "occupancy_exceeded"
ALERT_QUEUE_EXCEEDED = "queue_threshold_exceeded"
ALERT_RECOG_FAILURE_RATE = "recognition_failure_rate_high"
ALERT_STREAM_LATENCY = "stream_latency_high"
ALERT_RETENTION_FAILED = "retention_job_failed"
ALERT_CONSENT_EXPIRED = "consent_expired_attempt"
ALERT_TYPES = (
    ALERT_UNAUTHORIZED_MATCH,
    ALERT_RESTRICTED_ENTRY,
    ALERT_UNKNOWN_RESTRICTED,
    ALERT_LIVENESS_ATTACK,
    ALERT_MFA_CONFLICT,
    ALERT_CAMERA_OFFLINE,
    ALERT_CAMERA_TAMPER,
    ALERT_OCCUPANCY_EXCEEDED,
    ALERT_QUEUE_EXCEEDED,
    ALERT_RECOG_FAILURE_RATE,
    ALERT_STREAM_LATENCY,
    ALERT_RETENTION_FAILED,
    ALERT_CONSENT_EXPIRED,
)

# --- Reviews -------------------------------------------------------------------------
REVIEW_UNCERTAIN = "uncertain_match"
REVIEW_MFA_CONFLICT = "multi_factor_conflict"
REVIEW_SPOOF = "suspected_presentation_attack"
REVIEW_FALSE_POS = "false_positive_report"
REVIEW_FALSE_NEG = "false_negative_report"
REVIEW_POLICY_EXCEPTION = "policy_exception"
REVIEW_MANUAL = "manual_identity_verification"
REVIEW_REASONS = (
    REVIEW_UNCERTAIN,
    REVIEW_MFA_CONFLICT,
    REVIEW_SPOOF,
    REVIEW_FALSE_POS,
    REVIEW_FALSE_NEG,
    REVIEW_POLICY_EXCEPTION,
    REVIEW_MANUAL,
)

CASE_OPEN = "open"
CASE_IN_REVIEW = "in_review"
CASE_CLOSED = "closed"
CASE_STATUSES = (CASE_OPEN, CASE_IN_REVIEW, CASE_CLOSED)

ACTION_CONFIRM_MATCH = "confirm_match"
ACTION_REJECT_MATCH = "reject_match"
ACTION_MARK_UNKNOWN = "mark_unknown"
ACTION_INSUFFICIENT = "mark_insufficient_evidence"
ACTION_FLAG_SPOOF = "flag_spoof_attempt"
ACTION_OVERRIDE = "override_with_reason"
ACTION_REQUEST_EVIDENCE = "request_additional_evidence"
ACTION_CLOSE = "close_review"
REVIEW_ACTIONS = (
    ACTION_CONFIRM_MATCH,
    ACTION_REJECT_MATCH,
    ACTION_MARK_UNKNOWN,
    ACTION_INSUFFICIENT,
    ACTION_FLAG_SPOOF,
    ACTION_OVERRIDE,
    ACTION_REQUEST_EVIDENCE,
    ACTION_CLOSE,
)

# --- Enrollment ------------------------------------------------------------------------
ENROLLMENT_ACTIVE = "active"
ENROLLMENT_DISABLED = "disabled"
ENROLLMENT_EXPIRED = "expired"
ENROLLMENT_STATUSES = (ENROLLMENT_ACTIVE, ENROLLMENT_DISABLED, ENROLLMENT_EXPIRED)

# --- RBAC ---------------------------------------------------------------------------------
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_REVIEWER = "reviewer"
ROLE_VIEWER = "viewer"
ROLES = (ROLE_ADMIN, ROLE_OPERATOR, ROLE_REVIEWER, ROLE_VIEWER)

# --- EventBus topics / event types ----------------------------------------------------------
TOPIC_LIVE = "live"

EVT_TRACK_UPDATE = "track.update"
EVT_ZONE_EVENT = "zone.event"
EVT_RECOGNITION = "recognition.decision"
EVT_SESSION_STARTED = "session.started"
EVT_SESSION_CLOSED = "session.closed"
EVT_ALERT_RAISED = "alert.raised"
EVT_ALERT_UPDATED = "alert.updated"
EVT_OCCUPANCY = "occupancy.snapshot"
EVT_CAMERA_HEALTH = "camera.health"
EVT_ACCESS_EVENT = "access.event"
EVT_REVIEW_UPDATED = "review.updated"
EVT_RETENTION_DONE = "retention.completed"

# --- Spec §9 recognition decision vocabulary -------------------------------------------------
REC_AUTHORIZED = "authorized_match"
REC_UNAUTHORIZED = "unauthorized_match"
REC_UNKNOWN = "unknown"
REC_FACE_QUALITY = "face_quality_insufficient"
REC_MFA_CONFLICT = "multi_factor_conflict"
REC_MANUAL_REVIEW = "manual_review_required"
REC_POLICY_BLOCKED = "recognition_blocked_by_policy"
REC_LIVENESS_ATTACK = "liveness_suspected_attack"
SPEC_REC_DECISIONS = (
    REC_AUTHORIZED,
    REC_UNAUTHORIZED,
    REC_UNKNOWN,
    REC_UNCERTAIN,
    REC_FACE_QUALITY,
    REC_BLOCKED_POLICY,
    SPOOF_ATTACK,
    REC_MFA_CONFLICT,
    REC_MANUAL_REVIEW,
)

# --- Spec §9 multi-factor outcomes --------------------------------------------------------------
MFA_VERIFIED_MULTI = "verified_by_multiple_factors"
MFA_FACE_ONLY = "face_only_match"
MFA_CREDENTIAL_ONLY = "credential_only"
MFA_CONFLICT = "factor_conflict"
MFA_CREDENTIAL_DENIED = "credential_denied"
MFA_MANUAL_REVIEW = "manual_review_required"
MFA_OUTCOMES = (
    MFA_VERIFIED_MULTI,
    MFA_FACE_ONLY,
    MFA_CREDENTIAL_ONLY,
    MFA_CONFLICT,
    MFA_CREDENTIAL_DENIED,
    MFA_MANUAL_REVIEW,
)

# --- Spec §18 RBAC roles --------------------------------------------------------------------------
ROLE_SYSTEM_ADMIN = "system_admin"
ROLE_CAMERA_OPERATOR = "camera_operator"
ROLE_SECURITY_OPERATOR = "security_operator"
ROLE_REVIEWER = "reviewer"
ROLE_ENROLLMENT_MANAGER = "enrollment_manager"
ROLE_AUDITOR = "auditor"
ROLE_PRIVACY_OFFICER = "privacy_officer"
ROLE_INTEGRATION_SERVICE = "integration_service"
SPEC_ROLES = (
    ROLE_SYSTEM_ADMIN,
    ROLE_CAMERA_OPERATOR,
    ROLE_SECURITY_OPERATOR,
    ROLE_REVIEWER,
    ROLE_ENROLLMENT_MANAGER,
    ROLE_AUDITOR,
    ROLE_PRIVACY_OFFICER,
    ROLE_INTEGRATION_SERVICE,
    ROLE_VIEWER,
)

ADMIN_ROLES = (ROLE_SYSTEM_ADMIN,)
REVIEWER_ROLES = (ROLE_REVIEWER, ROLE_SECURITY_OPERATOR, ROLE_SYSTEM_ADMIN)
ENROLLMENT_ROLES = (ROLE_ENROLLMENT_MANAGER, ROLE_SYSTEM_ADMIN)
OPERATOR_ROLES = (ROLE_CAMERA_OPERATOR, ROLE_SECURITY_OPERATOR, ROLE_SYSTEM_ADMIN)
AUDIT_ROLES = (ROLE_AUDITOR, ROLE_PRIVACY_OFFICER, ROLE_SYSTEM_ADMIN)
INTEGRATION_ROLES = (ROLE_INTEGRATION_SERVICE, ROLE_SYSTEM_ADMIN)
