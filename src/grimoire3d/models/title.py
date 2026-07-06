"""Title setting as a pure data model extension."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .base import DataModel, register_extension


@dataclass(frozen=True, slots=True)
class TitleSetting(DataModel):
    """Simple title setting as an extension (not a hardcoded field)."""

    value: str = "Grimoire3D"
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "version": self.version}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TitleSetting:
        return cls(
            value=data.get("value", "Grimoire3D"),
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> TitleSetting:
        return replace(self, **changes)


register_extension("title", TitleSetting)