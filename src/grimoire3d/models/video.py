"""Video / window presentation settings as a pure data model extension."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .base import DataModel, register_extension


@dataclass(frozen=True, slots=True)
class VideoSettings(DataModel):
    """Video / window presentation settings.

    Adding new video-related settings is done by adding net-new fields
    to this small class (or creating yet another focused model).
    """

    width: int = 800
    height: int = 600
    vsync: bool = True
    clear_color: tuple[int, int, int, int] = (0, 0, 0, 255)
    version: int = 1

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if len(self.clear_color) != 4 or not all(0 <= c <= 255 for c in self.clear_color):
            raise ValueError("clear_color must be a 4-tuple of ints 0-255")

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "vsync": self.vsync,
            "clear_color": self.clear_color,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VideoSettings:
        return cls(
            width=data.get("width", 800),
            height=data.get("height", 600),
            vsync=data.get("vsync", True),
            clear_color=data.get("clear_color", (0, 0, 0, 255)),
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> VideoSettings:
        return replace(self, **changes)


register_extension("video", VideoSettings)