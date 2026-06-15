"""InputMap: action-to-binding configuration (Godot-style).

An InputMap is an immutable mapping from action name strings to the set of
hardware bindings that can trigger each action.  Callers never mutate an
InputMap in place; the ``with_*`` helpers return new instances.

Typical usage::

    from grimoire2d.models.input_binding import KeyBinding, GamepadButtonBinding
    from grimoire2d.models.gamepad_state import GamepadButton
    from grimoire2d.models.input_map import InputMap

    imap = InputMap.empty()
    imap = imap.with_binding("accept", KeyBinding("return"))
    imap = imap.with_binding("accept", GamepadButtonBinding(GamepadButton.A))
    imap = imap.with_binding("cancel", KeyBinding("escape"))
    imap = imap.with_binding("cancel", GamepadButtonBinding(GamepadButton.B))
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .base import DataModel
from .input_binding import (
    InputBinding,
    KeyBinding,
    MouseButtonBinding,
    GamepadButtonBinding,
    GamepadAxisBinding,
)
from .gamepad_state import GamepadAxis, GamepadButton


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _binding_to_dict(b: InputBinding) -> dict[str, Any]:
    if isinstance(b, KeyBinding):
        return {"type": "key", "key": b.key}
    if isinstance(b, MouseButtonBinding):
        return {"type": "mouse_button", "button": b.button}
    if isinstance(b, GamepadButtonBinding):
        return {"type": "gamepad_button", "button": b.button.value}
    if isinstance(b, GamepadAxisBinding):
        return {
            "type": "gamepad_axis",
            "axis": b.axis.value,
            "direction": b.direction,
            "threshold": b.threshold,
        }
    raise TypeError(f"Unknown binding type: {type(b)}")  # pragma: no cover


def _binding_from_dict(data: dict[str, Any]) -> InputBinding:
    kind = data["type"]
    if kind == "key":
        return KeyBinding(key=data["key"])
    if kind == "mouse_button":
        return MouseButtonBinding(button=data["button"])
    if kind == "gamepad_button":
        return GamepadButtonBinding(button=GamepadButton(data["button"]))
    if kind == "gamepad_axis":
        return GamepadAxisBinding(
            axis=GamepadAxis(data["axis"]),
            direction=data.get("direction", 1),
            threshold=data.get("threshold", 0.5),
        )
    raise ValueError(f"Unknown binding type: {kind!r}")


# ---------------------------------------------------------------------------
# InputMap
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InputMap(DataModel):
    """Immutable mapping from action names to the bindings that trigger them.

    actions: dict[str, frozenset[InputBinding]] — keys are action names
             (e.g. ``"jump"``, ``"accept"``); values are the set of hardware
             bindings that activate the action.

    An action fires when *any* of its bindings is active (OR semantics),
    consistent with Godot's input mapping model.
    """

    actions: dict[str, frozenset[InputBinding]] = field(default_factory=dict)
    version: int = 1

    def get_bindings(self, action: str) -> frozenset[InputBinding]:
        """Return all bindings registered for *action* (empty set if unknown)."""
        return self.actions.get(action, frozenset())

    def has_action(self, action: str) -> bool:
        """Return True if *action* exists (even if it has no bindings)."""
        return action in self.actions

    def action_names(self) -> frozenset[str]:
        """Return all defined action names."""
        return frozenset(self.actions.keys())

    # ------------------------------------------------------------------ #
    # Immutable mutation helpers
    # ------------------------------------------------------------------ #

    def with_binding(self, action: str, binding: InputBinding) -> InputMap:
        """Return a new InputMap with *binding* added to *action*."""
        existing = self.actions.get(action, frozenset())
        new_actions = {**self.actions, action: existing | {binding}}
        return replace(self, actions=new_actions)

    def without_binding(self, action: str, binding: InputBinding) -> InputMap:
        """Return a new InputMap with *binding* removed from *action*."""
        existing = self.actions.get(action, frozenset())
        new_bindings = existing - {binding}
        new_actions = {**self.actions, action: new_bindings}
        return replace(self, actions=new_actions)

    def with_action(
        self, action: str, bindings: frozenset[InputBinding] | None = None
    ) -> InputMap:
        """Return a new InputMap ensuring *action* exists with the given bindings."""
        new_actions = {**self.actions, action: bindings or frozenset()}
        return replace(self, actions=new_actions)

    def without_action(self, action: str) -> InputMap:
        """Return a new InputMap with *action* removed entirely."""
        new_actions = {k: v for k, v in self.actions.items() if k != action}
        return replace(self, actions=new_actions)

    # ------------------------------------------------------------------ #
    # DataModel protocol
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": {
                name: [
                    _binding_to_dict(b) for b in sorted(bindings, key=lambda b: repr(b))
                ]
                for name, bindings in self.actions.items()
            },
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InputMap:
        actions = {
            name: frozenset(_binding_from_dict(b) for b in bindings)
            for name, bindings in data.get("actions", {}).items()
        }
        return cls(actions=actions, version=data.get("version", 1))

    def with_updates(self, **changes: Any) -> InputMap:
        return replace(self, **changes)

    @classmethod
    def empty(cls) -> InputMap:
        """Construct an InputMap with no actions defined."""
        return cls()
