"""Frame timing and performance settings as a pure data model extension."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .base import DataModel, register_extension


@dataclass(frozen=True, slots=True)
class TimingSettings(DataModel):
    """Frame timing and performance settings."""

    target_fps: int = 60
    version: int = 1

    def __post_init__(self) -> None:
        if self.target_fps <= 0:
            raise ValueError("target_fps must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_fps": self.target_fps,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimingSettings:
        return cls(
            target_fps=data.get("target_fps", 60),
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> TimingSettings:
        return replace(self, **changes)


register_extension("timing", TimingSettings)