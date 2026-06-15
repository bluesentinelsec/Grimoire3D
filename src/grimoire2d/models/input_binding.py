"""Input binding types: the vocabulary for mapping hardware events to actions.

Each binding type represents one physical input that can activate a
logical action. Combine multiple bindings under the same action name in
InputMap to implement "any of these triggers the action" semantics —
identical to Godot's action-mapping model.

All binding types are frozen dataclasses so they can be stored in
frozensets and used as dict keys inside InputMap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .gamepad_state import GamepadAxis, GamepadButton


@dataclass(frozen=True, slots=True)
class KeyBinding:
    """A keyboard key identified by its pygame name (e.g. ``"space"``, ``"a"``, ``"left"``)."""

    key: str


@dataclass(frozen=True, slots=True)
class MouseButtonBinding:
    """A mouse button identified by pygame button index (1=left, 2=middle, 3=right)."""

    button: int


@dataclass(frozen=True, slots=True)
class GamepadButtonBinding:
    """An Xbox-layout gamepad button."""

    button: GamepadButton


@dataclass(frozen=True, slots=True)
class GamepadAxisBinding:
    """An analog axis treated as a digital button once it crosses a threshold.

    direction:  +1 to fire when the axis is pushed in the positive direction,
                -1 for the negative direction.
    threshold:  absolute value the axis must reach before the action fires.
                Defaults to 0.5, which gives a sensible deadband for sticks.
                For triggers (which rest at -1.0 and rise to +1.0) use a
                direction of +1 with threshold ~0.0 to fire on any pull.
    """

    axis: GamepadAxis
    direction: int = 1
    threshold: float = 0.5


#: Union type for any concrete binding.  Use this as the element type when
#: storing bindings in a collection.
InputBinding = Union[
    KeyBinding,
    MouseButtonBinding,
    GamepadButtonBinding,
    GamepadAxisBinding,
]
