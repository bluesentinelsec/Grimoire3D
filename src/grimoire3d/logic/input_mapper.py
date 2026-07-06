"""Input mapper: translates a RawInputFrame into logical action frozensets.

This is the bridge between the hardware-snapshot layer (RawInputFrame) and
the simulation layer (InputFrame / InputSource).  It evaluates every binding
registered in an InputMap against the current hardware state and returns the
set of active action names.

All functions here are pure and testable without pygame or a display.
"""

from __future__ import annotations

from grimoire3d.models.gamepad_state import GamepadState
from grimoire3d.models.input_binding import (
    GamepadAxisBinding,
    GamepadButtonBinding,
    InputBinding,
    KeyBinding,
    MouseButtonBinding,
)
from grimoire3d.models.input_map import InputMap
from grimoire3d.models.mouse_state import MouseButton
from grimoire3d.models.raw_input_frame import RawInputFrame
from grimoire3d.logic.gamepad_ops import is_axis_pressed


# Map pygame mouse button index → MouseButton enum
_PYGAME_MOUSE_MAP: dict[int, MouseButton] = {
    1: MouseButton.LEFT,
    2: MouseButton.MIDDLE,
    3: MouseButton.RIGHT,
    4: MouseButton.BACK,
    5: MouseButton.FORWARD,
}


def _is_binding_active(
    binding: InputBinding,
    raw: RawInputFrame,
    pad_id: int | None,
) -> bool:
    """Return True if *binding* is currently active given *raw* hardware state.

    Args:
        binding: the specific binding to evaluate
        raw:     complete hardware snapshot for the current tick
        pad_id:  which gamepad slot to check for GamepadButton / GamepadAxis
                 bindings.  When None, all connected pads are checked and the
                 binding fires if *any* of them satisfy it.

    Returns:
        True when the binding's input condition is met.
    """
    if isinstance(binding, KeyBinding):
        return binding.key in raw.keys_held

    if isinstance(binding, MouseButtonBinding):
        mapped = _PYGAME_MOUSE_MAP.get(binding.button)
        if mapped is None:
            return False
        return mapped in raw.mouse.buttons

    if isinstance(binding, GamepadButtonBinding):
        pads = _resolve_pads(raw, pad_id)
        return any(pad.connected and binding.button in pad.buttons for pad in pads)

    if isinstance(binding, GamepadAxisBinding):
        pads = _resolve_pads(raw, pad_id)
        return any(
            pad.connected
            and is_axis_pressed(pad, binding.axis, binding.direction, binding.threshold)
            for pad in pads
        )

    return False  # pragma: no cover — exhaustive by type union


def _resolve_pads(raw: RawInputFrame, pad_id: int | None) -> list[GamepadState]:
    """Return the list of GamepadState objects to evaluate for a binding."""
    if pad_id is not None:
        return [raw.get_pad(pad_id)]
    return list(raw.gamepads.values())


def map_actions(
    raw: RawInputFrame,
    input_map: InputMap,
    pad_id: int | None = None,
) -> frozenset[str]:
    """Evaluate all actions in *input_map* against *raw* and return active ones.

    An action is active when at least one of its registered bindings is active
    (OR semantics, identical to Godot's action-mapping model).

    Args:
        raw:       complete hardware snapshot for this tick
        input_map: the configured action→binding table
        pad_id:    restrict gamepad binding checks to a specific slot;
                   pass None to accept input from any connected gamepad

    Returns:
        frozenset of action name strings that are currently active.
    """
    active: set[str] = set()
    for action, bindings in input_map.actions.items():
        if any(_is_binding_active(b, raw, pad_id) for b in bindings):
            active.add(action)
    return frozenset(active)
