"""RawInputFrame: a complete hardware-level snapshot for one simulation tick.

This is the output of InputManager.poll() and the input to input_mapper.
It carries the full state of every supported input device so that the
mapping layer can evaluate any combination of bindings without needing
to re-query hardware.

The presentation layer produces RawInputFrames; the logic layer consumes
them to build action-level InputFrames — preserving the strict
data / logic / presentation separation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .base import DataModel
from .gamepad_state import GamepadState
from .mouse_state import MouseState


@dataclass(frozen=True, slots=True)
class RawInputFrame(DataModel):
    """Complete hardware snapshot captured at simulation *tick*.

    tick:       the simulation tick this snapshot was taken at
    keys_held:  frozenset of lowercase pygame key-name strings currently
                pressed (e.g. ``"space"``, ``"left"``, ``"a"``)
    mouse:      full mouse state for this tick
    gamepads:   mapping from logical pad slot (0–3) to its snapshot;
                only slots with connected pads are guaranteed to be present,
                but callers may receive a disconnected sentinel
    """

    tick: int = 0
    keys_held: frozenset[str] = frozenset()
    mouse: MouseState = field(default_factory=MouseState)
    gamepads: dict[int, GamepadState] = field(default_factory=dict)
    version: int = 1

    def get_pad(self, pad_id: int) -> GamepadState:
        """Return the state for *pad_id*, or a disconnected sentinel if absent."""
        return self.gamepads.get(pad_id, GamepadState.disconnected(pad_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "keys_held": sorted(self.keys_held),
            "mouse": self.mouse.to_dict(),
            "gamepads": {str(k): v.to_dict() for k, v in self.gamepads.items()},
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawInputFrame:
        gamepads = {
            int(k): GamepadState.from_dict(v)
            for k, v in data.get("gamepads", {}).items()
        }
        return cls(
            tick=data.get("tick", 0),
            keys_held=frozenset(data.get("keys_held", [])),
            mouse=MouseState.from_dict(data.get("mouse", {})),
            gamepads=gamepads,
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> RawInputFrame:
        return replace(self, **changes)
