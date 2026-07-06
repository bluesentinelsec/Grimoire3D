"""Pure gamepad math helpers.

All functions here are deterministic, side-effect-free, and fully
testable without pygame or a physical controller.
"""

from __future__ import annotations

import math

from grimoire3d.models.gamepad_state import GamepadAxis, GamepadState


def deadzone(
    value: float,
    inner: float = 0.1,
    outer: float = 0.95,
) -> float:
    """Apply a symmetric inner/outer deadzone to a raw axis value.

    Values within *inner* of centre are snapped to 0.0 (eliminates stick
    drift). Values at or beyond *outer* are snapped to ±1.0 (ensures full
    range is reachable). The remaining range is linearly remapped to
    [0.0, 1.0] to maintain smooth analog response.

    Args:
        value: raw axis value in [-1.0, 1.0]
        inner: fraction of travel to treat as neutral dead band
        outer: fraction of travel at which the axis is considered fully pressed

    Returns:
        Deadzoned value in [-1.0, 1.0].
    """
    if abs(value) < inner:
        return 0.0
    if abs(value) >= outer:
        return math.copysign(1.0, value)
    sign = math.copysign(1.0, value)
    remapped = (abs(value) - inner) / (outer - inner)
    return sign * remapped


def get_stick_vector(
    state: GamepadState,
    x_axis: GamepadAxis,
    y_axis: GamepadAxis,
    inner_deadzone: float = 0.1,
    outer_deadzone: float = 0.95,
) -> tuple[float, float]:
    """Return a deadzoned (x, y) vector for a two-axis stick.

    The Y axis from Xbox controllers is inverted relative to screen space
    (-1.0 = up, +1.0 = down). This function corrects that inversion so the
    returned vector follows the mathematical convention where positive Y is up.

    Returns:
        (x, y) with each component in [-1.0, 1.0] after deadzone application.
    """
    raw_x = state.get_axis(x_axis)
    raw_y = state.get_axis(y_axis)
    dz_x = deadzone(raw_x, inner_deadzone, outer_deadzone)
    dz_y = deadzone(raw_y, inner_deadzone, outer_deadzone)
    return (dz_x, -dz_y)


def trigger_value(state: GamepadState, axis: GamepadAxis) -> float:
    """Return the trigger pull as a clean [0.0, 1.0] value.

    pygame-ce reports triggers in the range [-1.0 (released), +1.0 (pressed)].
    This function maps that to the intuitive [0.0, 1.0] range.

    Args:
        state: current gamepad snapshot
        axis:  must be LEFT_TRIGGER or RIGHT_TRIGGER

    Returns:
        0.0 (fully released) to 1.0 (fully pressed).
    """
    raw = state.get_axis(axis)
    return (raw + 1.0) / 2.0


def is_axis_pressed(
    state: GamepadState,
    axis: GamepadAxis,
    direction: int = 1,
    threshold: float = 0.5,
) -> bool:
    """Return True when an analog axis exceeds *threshold* in *direction*.

    This is the axis-as-button primitive.  For trigger axes use
    ``trigger_value(state, axis) >= threshold`` to work in the natural
    [0.0, 1.0] range.

    Args:
        state:     current gamepad snapshot
        axis:      which axis to evaluate
        direction: +1 to test positive deflection, -1 for negative
        threshold: magnitude (in the raw [-1.0, 1.0] range) required to
                   consider the axis "pressed"; default 0.5

    Returns:
        True if the axis value in *direction* meets or exceeds *threshold*.
    """
    value = state.get_axis(axis)
    if direction > 0:
        return value >= threshold
    return value <= -threshold
