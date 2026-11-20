"""Model & threshold registry with versions, shadow testing, and rollback (spec §19)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.common.utils import utcnow


@dataclass
class ModelVersion:
    """A registered model artifact with rollout state."""

    name: str
    version: str
    path: str | None = None
    stage: str = "production"  # shadow | canary | production | rolled_back
    registered_at: datetime = field(default_factory=utcnow)
    metrics: dict = field(default_factory=dict)


class ModelRegistry:
    """In-memory model/threshold registry supporting shadow, canary, and rollback."""

    def __init__(self) -> None:
        self._models: dict[str, list[ModelVersion]] = {}
        self._thresholds: dict[str, dict[str, float]] = {}

    def register(self, model: ModelVersion) -> ModelVersion:
        self._models.setdefault(model.name, []).append(model)
        return model

    def active(self, name: str, stage: str = "production") -> ModelVersion | None:
        for mv in reversed(self._models.get(name, [])):
            if mv.stage == stage:
                return mv
        return None

    def versions(self, name: str) -> list[ModelVersion]:
        return list(self._models.get(name, []))

    def promote(self, name: str, version: str, stage: str) -> ModelVersion | None:
        for mv in self._models.get(name, []):
            if mv.version == version:
                mv.stage = stage
                return mv
        return None

    def rollback(self, name: str) -> ModelVersion | None:
        chain = self._models.get(name, [])
        for mv in reversed(chain):
            if mv.stage in ("canary", "shadow"):
                mv.stage = "rolled_back"
        for mv in reversed(chain):
            if mv.stage == "production":
                return mv
        return None

    def set_threshold(self, scope: str, values: dict[str, float]) -> None:
        self._thresholds[scope] = dict(values)

    def thresholds(self, scope: str) -> dict[str, float]:
        return dict(self._thresholds.get(scope, {}))

    def snapshot(self) -> dict:
        return {
            "models": {
                name: [
                    {"version": m.version, "stage": m.stage, "registered_at": m.registered_at.isoformat()}
                    for m in chain
                ]
                for name, chain in self._models.items()
            },
            "thresholds": {k: dict(v) for k, v in self._thresholds.items()},
        }


registry = ModelRegistry()
