# consent-vision-ops

Production-ready Python computer-vision and access-operations platform for controlled,
consent-based camera areas.

The platform detects people entering monitored areas, detects and tracks faces, assesses
face quality, and — **only** for explicitly enrolled and consented people — performs
identity recognition. Unknown persons remain anonymous and never receive persistent
profiles. Recognition is disabled by default and gated by consent, policy, quality,
liveness, and multi-factor correlation, with immutable audit logs and human review
for uncertain decisions.

## Core principles

- Face recognition is optional, **disabled by default**, and requires documented consent
  and a valid policy/legal basis.
- Unknown persons remain anonymous; no persistent profiles are auto-created.
- Face recognition is one signal only — badge, QR, PIN, NFC, turnstile, and
  access-control correlation are first-class inputs.
- No inference of emotions, health status, demographics, or other sensitive attributes.
- No raw video, face crops, or embeddings are retained by default.
- Uncertain, conflicting, or low-confidence identity decisions require human review.
- Immutable audit logs cover enrollment, recognition, review, export, policy changes,
  retention actions, and deletion.

## Architecture

```text
Camera / Video / Image / Access-Control Event
    ↓
Frame decoding and stream health checks
    ↓
Person detection → Person tracking
    ↓
Face detection → alignment/landmarks/pose → Face quality
    ↓
Zone detection and entry/exit events
    ↓
Optional liveness / spoof-detection
    ↓
Consent + policy + authorization validation
    ↓
Optional embedding generation and gallery matching (pgvector, cosine)
    ↓
Multi-frame confirmation + multi-factor correlation
    ↓
Known-person or anonymous visit sessions
    ↓
Alerts, dashboard, WebSocket events, reports, audit logs
```

### Service modules (spec §5)

`ingestion`, `frame_processor`, `person_detection`, `face_detection`, `face_quality`,
`landmark_pose`, `tracking`, `zones`, `liveness`, `recognition`,
`multi_factor_verification`, `consent_policy`, `sessions`, `occupancy_analytics`,
`camera_health`, `alerts`, `review_workflow`, `reporting`, `retention`, `audit`,
`storage`, `api`, `websocket`, `observability`.

## Repository structure

```text
app/
├── api/            FastAPI routers (v1)
├── auth/           API-key / JWT auth, RBAC dependencies
├── common/         enums, event bus, utils
├── config/         pydantic-settings
├── db/             async engine/session
├── models/         SQLAlchemy ORM (persons, ops, events, governance)
├── schemas/        Pydantic v2 request/response schemas
├── repositories/   async data access
├── services/       domain services (detection, tracking, quality, recognition, ...)
├── workers/        background tasks (retention, camera health, reporting)
├── observability/  Prometheus metrics, structured logs
└── main.py         FastAPI app factory
migrations/         Alembic
tests/              unit / integration / API / acceptance tests
docker/             grafana / prometheus config
frontend/           dashboard
```

## Local development (CPU-only)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -e ".[dev]"           # CPU stack only
copy .env.example .env            # adjust as needed
uvicorn app.main:app --reload     # http://localhost:8000/docs
pytest                            # run the test suite
```

The default `database_url` is SQLite (`sqlite+aiosqlite`) so the platform runs with no
external services. For production use PostgreSQL with pgvector (`postgresql+asyncpg://...`)
and Redis; tables are created via Alembic (`alembic upgrade head`).

Optional heavy CV dependencies (YOLO, InsightFace, MediaPipe) install via
`pip install -e ".[cv]"`; the platform runs built-in deterministic detectors and a
hashing-based embedder without them and gracefully upgrades when they are present.

## Production deployment (Docker)

```bash
docker compose up -d              # api, worker, redis, postgres+pgvector, minio,
                                  # prometheus, grafana, otel-collector (optional)
docker compose exec api alembic upgrade head
```

- `Dockerfile.api` — FastAPI API image
- `Dockerfile.worker.cpu` — CPU background worker
- `Dockerfile.worker.gpu` — CUDA-enabled worker (NVIDIA container toolkit required)

Environment variables (database, Redis, object storage, encryption, camera credentials,
model paths, thresholds, consent, retention, alert integrations, GPU, ONNX Runtime,
batching, frame skipping, bounded queues) are documented in `.env.example`.

Performance target: < 500 ms end-to-end latency per processed frame on suitable GPU
hardware (frame skipping, bounded queues, stream isolation, and graceful degradation
are built in).

## API overview

REST endpoints under `/v1` (cameras, zones, persons, consents, enrollments, sessions,
detections, recognition events, live tracks, occupancy, queue metrics, access events,
alert rules, alerts, review cases, reports, retention, audit) plus:

- `GET /health`, `GET /ready`, `GET /metrics` (Prometheus)
- `WS /v1/live/events` — live track, alert, occupancy, and camera-health events

All list endpoints use cursor pagination, filtering, sorting, RBAC, and request
correlation IDs.

## Security & governance

- Stream credentials encrypted at rest (Fernet envelope encryption).
- Consent expiration/revocation disables matching immediately.
- Deletion evidence and audit logs for all sensitive actions.
- Roles: `system_admin`, `camera_operator`, `security_operator`, `reviewer`,
  `enrollment_manager`, `auditor`, `privacy_officer`, `integration_service`.

## License

Proprietary — Platform Team.
