"""Gamepad state models: Xbox-layout enumerations and per-frame snapshot.

Supports up to 4 simultaneously-connected gamepads. All axis values range
from -1.0 to +1.0 as reported by pygame-ce. Triggers rest at -1.0 (fully
released) and peak at +1.0 (fully pressed) on the normalised axis scale;
use gamepad_ops.trigger_value() to convert to a clean [0.0, 1.0] range.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

from .base import DataModel


class GamepadButton(Enum):
    """Xbox-layout face buttons, shoulder buttons, sticks, and D-pad."""

    A = "a"
    B = "b"
    X = "x"
    Y = "y"
    LB = "lb"
    RB = "rb"
    BACK = "back"
    START = "start"
    GUIDE = "guide"
    LEFT_STICK = "left_stick"
    RIGHT_STICK = "right_stick"
    DPAD_UP = "dpad_up"
    DPAD_DOWN = "dpad_down"
    DPAD_LEFT = "dpad_left"
    DPAD_RIGHT = "dpad_right"


class GamepadAxis(Enum):
    """Xbox-layout analog axes.

    LEFT_Y / RIGHT_Y are typically inverted relative to screen space:
    -1.0 = up / away from player, +1.0 = down / toward player.
    Use gamepad_ops.get_stick_vector() to obtain a corrected 2-D vector.
    """

    LEFT_X = "left_x"
    LEFT_Y = "left_y"
    RIGHT_X = "right_x"
    RIGHT_Y = "right_y"
    LEFT_TRIGGER = "left_trigger"
    RIGHT_TRIGGER = "right_trigger"


@dataclass(frozen=True, slots=True)
class GamepadState(DataModel):
    """Pure snapshot of one gamepad's state at a single simulation tick.

    pad_id:    logical slot index in the range [0, 3]
    connected: False when the device has been unplugged; callers should
               stop querying hardware for disconnected pads
    buttons:   frozenset of GamepadButton values currently held
    axes:      dict from GamepadAxis to float in [-1.0, 1.0] — treat as
               read-only; all mutations return a new GamepadState
    """

    pad_id: int = 0
    connected: bool = False
    buttons: frozenset[GamepadButton] = frozenset()
    axes: dict[GamepadAxis, float] = field(default_factory=dict)
    version: int = 1

    def is_button_pressed(self, button: GamepadButton) -> bool:
        """Return True if *button* is in the current held set."""
        return button in self.buttons

    def get_axis(self, axis: GamepadAxis) -> float:
        """Return the current value for *axis*, defaulting to 0.0."""
        return self.axes.get(axis, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pad_id": self.pad_id,
            "connected": self.connected,
            "buttons": sorted(b.value for b in self.buttons),
            "axes": {a.value: v for a, v in self.axes.items()},
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GamepadState:
        buttons = frozenset(GamepadButton(b) for b in data.get("buttons", []))
        axes = {GamepadAxis(k): float(v) for k, v in data.get("axes", {}).items()}
        return cls(
            pad_id=data.get("pad_id", 0),
            connected=data.get("connected", False),
            buttons=buttons,
            axes=axes,
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> GamepadState:
        return replace(self, **changes)

    @classmethod
    def disconnected(cls, pad_id: int) -> GamepadState:
        """Construct a sentinel state for an unplugged slot."""
        return cls(pad_id=pad_id, connected=False)
