from app.models import Base

def test_metadata_contains_all_tables_and_foreign_keys():
    expected = {"camera_sources", "camera_zones", "visit_sessions", "occupancy_snapshots", "camera_health_events", "person_profiles", "face_enrollments", "face_detections", "recognition_events", "access_verification_events", "liveness_events", "alert_rules", "alerts", "review_cases", "review_actions", "retained_media", "audit_logs"}
    assert expected <= set(Base.metadata.tables)
    assert any(fk.target_fullname == "camera_sources.camera_id" for fk in Base.metadata.tables["camera_zones"].foreign_keys)
