"""Mouse state model: button enumeration and per-frame snapshot.

Tracks physical screen coordinates and, when a Viewport is available,
the corresponding virtual (game-space) coordinates after letterbox
compensation. Scroll delta accumulates all wheel events for the frame.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from .base import DataModel


class MouseButton(Enum):
    """Standard mouse buttons."""

    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"
    BACK = "back"
    FORWARD = "forward"


@dataclass(frozen=True, slots=True)
class MouseState(DataModel):
    """Pure snapshot of mouse state at a single simulation tick.

    position:         physical pixel coordinates (x, y) relative to the
                      top-left corner of the OS window
    virtual_position: game-space coordinates after letterbox / scale mapping;
                      equals position when no virtual resolution is active
    buttons:          frozenset of MouseButton values currently held
    scroll_delta:     (dx, dy) scroll wheel motion accumulated this frame;
                      positive y = scroll up / away from user on most platforms
    """

    position: tuple[float, float] = (0.0, 0.0)
    virtual_position: tuple[float, float] = (0.0, 0.0)
    buttons: frozenset[MouseButton] = frozenset()
    scroll_delta: tuple[float, float] = (0.0, 0.0)
    version: int = 1

    def is_button_pressed(self, button: MouseButton) -> bool:
        """Return True if *button* is currently held."""
        return button in self.buttons

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": list(self.position),
            "virtual_position": list(self.virtual_position),
            "buttons": sorted(b.value for b in self.buttons),
            "scroll_delta": list(self.scroll_delta),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MouseState:
        pos = data.get("position", [0.0, 0.0])
        vpos = data.get("virtual_position", [0.0, 0.0])
        scroll = data.get("scroll_delta", [0.0, 0.0])
        buttons = frozenset(MouseButton(b) for b in data.get("buttons", []))
        return cls(
            position=(float(pos[0]), float(pos[1])),
            virtual_position=(float(vpos[0]), float(vpos[1])),
            buttons=buttons,
            scroll_delta=(float(scroll[0]), float(scroll[1])),
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> MouseState:
        return replace(self, **changes)
