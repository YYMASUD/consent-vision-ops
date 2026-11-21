"""Visit-session lifecycle operations."""
import uuid
from app.common.enums import SESSION_ACTIVE, SESSION_ENDED
from app.common.utils import utcnow
from app.models.ops import VisitSession

async def start_session(repository, camera_id, track_id, *, zone_id=None, person_id=None, anonymous_subject_id=None, timestamp=None):
    now = timestamp or utcnow()
    session = VisitSession(camera_id=uuid.UUID(str(camera_id)), track_id=uuid.UUID(str(track_id)), zone_id=uuid.UUID(str(zone_id)) if zone_id else None, person_id=uuid.UUID(str(person_id)) if person_id else None, anonymous_subject_id=uuid.UUID(str(anonymous_subject_id)) if anonymous_subject_id else None, status=SESSION_ACTIVE, started_at=now, last_seen_at=now)
    repository.add(session); await repository.flush(); return session

async def touch_session(repository, session, *, timestamp=None):
    session.last_seen_at = timestamp or utcnow(); await repository.flush(); return session

async def end_session(repository, session, *, timestamp=None):
    now = timestamp or utcnow(); session.status = SESSION_ENDED; session.ended_at = now; session.last_seen_at = now; await repository.flush(); return session

