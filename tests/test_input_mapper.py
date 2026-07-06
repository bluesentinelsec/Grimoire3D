"""Tests for logic.input_mapper — map_actions and binding evaluation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire3d.logic.input_mapper import map_actions
from grimoire3d.models.gamepad_state import GamepadAxis, GamepadButton, GamepadState
from grimoire3d.models.input_binding import (
    GamepadAxisBinding,
    GamepadButtonBinding,
    KeyBinding,
    MouseButtonBinding,
)
from grimoire3d.models.input_map import InputMap
from grimoire3d.models.mouse_state import MouseButton, MouseState
from grimoire3d.models.raw_input_frame import RawInputFrame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _raw(
    keys: frozenset[str] = frozenset(),
    mouse_buttons: frozenset[MouseButton] = frozenset(),
    gamepads: dict[int, GamepadState] | None = None,
) -> RawInputFrame:
    return RawInputFrame(
        tick=     0,
        keys_held= keys,
        mouse=    MouseState(buttons=mouse_buttons),
        gamepads= gamepads or {},
    )


def _pad(
    pad_id: int = 0,
    buttons: frozenset[GamepadButton] = frozenset(),
    axes: dict[GamepadAxis, float] | None = None,
) -> GamepadState:
    return GamepadState(
        pad_id=    pad_id,
        connected= True,
        buttons=   buttons,
        axes=      axes or {},
    )


# ---------------------------------------------------------------------------
# Key bindings
# ---------------------------------------------------------------------------

class TestKeyBindingMapping(unittest.TestCase):

    def setUp(self):
        self.imap = (
            InputMap.empty()
            .with_binding("jump",  KeyBinding("space"))
            .with_binding("left",  KeyBinding("a"))
            .with_binding("left",  KeyBinding("left"))
        )

    def test_key_pressed_activates_action(self):
        actions = map_actions(_raw(frozenset(["space"])), self.imap)
        self.assertIn("jump", actions)

    def test_alternate_key_activates_action(self):
        actions = map_actions(_raw(frozenset(["left"])), self.imap)
        self.assertIn("left", actions)

    def test_no_key_pressed_no_action(self):
        actions = map_actions(_raw(), self.imap)
        self.assertNotIn("jump", actions)

    def test_multiple_actions_simultaneously(self):
        actions = map_actions(_raw(frozenset(["space", "a"])), self.imap)
        self.assertIn("jump", actions)
        self.assertIn("left", actions)

    def test_case_sensitivity(self):
        # Key names must match exactly; "Space" ≠ "space"
        actions = map_actions(_raw(frozenset(["Space"])), self.imap)
        self.assertNotIn("jump", actions)


# ---------------------------------------------------------------------------
# Mouse button bindings
# ---------------------------------------------------------------------------

class TestMouseButtonBindingMapping(unittest.TestCase):

    def setUp(self):
        self.imap = InputMap.empty().with_binding("fire", MouseButtonBinding(1))

    def test_left_button_activates_fire(self):
        actions = map_actions(
            _raw(mouse_buttons=frozenset({MouseButton.LEFT})), self.imap
        )
        self.assertIn("fire", actions)

    def test_right_button_does_not_activate_fire(self):
        actions = map_actions(
            _raw(mouse_buttons=frozenset({MouseButton.RIGHT})), self.imap
        )
        self.assertNotIn("fire", actions)

    def test_no_button_no_action(self):
        actions = map_actions(_raw(), self.imap)
        self.assertNotIn("fire", actions)


# ---------------------------------------------------------------------------
# Gamepad button bindings
# ---------------------------------------------------------------------------

class TestGamepadButtonBindingMapping(unittest.TestCase):

    def setUp(self):
        self.imap = InputMap.empty().with_binding(
            "accept", GamepadButtonBinding(GamepadButton.A)
        )

    def test_button_a_activates_accept(self):
        raw = _raw(gamepads={0: _pad(buttons=frozenset({GamepadButton.A}))})
        self.assertIn("accept", map_actions(raw, self.imap))

    def test_button_b_does_not_activate_accept(self):
        raw = _raw(gamepads={0: _pad(buttons=frozenset({GamepadButton.B}))})
        self.assertNotIn("accept", map_actions(raw, self.imap))

    def test_disconnected_pad_does_not_activate(self):
        disconnected = GamepadState(pad_id=0, connected=False, buttons=frozenset({GamepadButton.A}))
        raw = _raw(gamepads={0: disconnected})
        self.assertNotIn("accept", map_actions(raw, self.imap))

    def test_pad_id_filter_correct_slot(self):
        pad0 = _pad(pad_id=0)
        pad1 = _pad(pad_id=1, buttons=frozenset({GamepadButton.A}))
        raw  = _raw(gamepads={0: pad0, 1: pad1})
        # Check with pad_id=1 → should match
        self.assertIn("accept", map_actions(raw, self.imap, pad_id=1))
        # Check with pad_id=0 → no A pressed on pad 0
        self.assertNotIn("accept", map_actions(raw, self.imap, pad_id=0))

    def test_no_pad_id_accepts_any_connected_pad(self):
        pad1 = _pad(pad_id=1, buttons=frozenset({GamepadButton.A}))
        raw  = _raw(gamepads={1: pad1})
        # pad_id=None → any pad
        self.assertIn("accept", map_actions(raw, self.imap, pad_id=None))


# ---------------------------------------------------------------------------
# Gamepad axis bindings
# ---------------------------------------------------------------------------

class TestGamepadAxisBindingMapping(unittest.TestCase):

    def setUp(self):
        self.imap = InputMap.empty().with_binding(
            "move_right",
            GamepadAxisBinding(GamepadAxis.LEFT_X, direction=1, threshold=0.5),
        )

    def test_axis_above_threshold_activates_action(self):
        raw = _raw(gamepads={0: _pad(axes={GamepadAxis.LEFT_X: 0.8})})
        self.assertIn("move_right", map_actions(raw, self.imap))

    def test_axis_below_threshold_no_action(self):
        raw = _raw(gamepads={0: _pad(axes={GamepadAxis.LEFT_X: 0.3})})
        self.assertNotIn("move_right", map_actions(raw, self.imap))

    def test_negative_direction(self):
        imap = InputMap.empty().with_binding(
            "move_left",
            GamepadAxisBinding(GamepadAxis.LEFT_X, direction=-1, threshold=0.5),
        )
        raw = _raw(gamepads={0: _pad(axes={GamepadAxis.LEFT_X: -0.8})})
        self.assertIn("move_left", map_actions(raw, imap))

    def test_trigger_as_button(self):
        # Triggers rest at -1.0; direction=1 with threshold 0.0 means any pull
        imap = InputMap.empty().with_binding(
            "brake",
            GamepadAxisBinding(GamepadAxis.LEFT_TRIGGER, direction=1, threshold=0.0),
        )
        raw = _raw(gamepads={0: _pad(axes={GamepadAxis.LEFT_TRIGGER: 0.5})})
        self.assertIn("brake", map_actions(raw, imap))


# ---------------------------------------------------------------------------
# Mixed bindings (OR semantics)
# ---------------------------------------------------------------------------

class TestMixedBindingOrSemantics(unittest.TestCase):

    def setUp(self):
        self.imap = (
            InputMap.empty()
            .with_binding("accept", KeyBinding("return"))
            .with_binding("accept", GamepadButtonBinding(GamepadButton.A))
        )

    def test_keyboard_triggers_accept(self):
        raw = _raw(frozenset(["return"]))
        self.assertIn("accept", map_actions(raw, self.imap))

    def test_gamepad_triggers_accept(self):
        raw = _raw(gamepads={0: _pad(buttons=frozenset({GamepadButton.A}))})
        self.assertIn("accept", map_actions(raw, self.imap))

    def test_both_active_still_produces_one_action(self):
        raw = _raw(
            frozenset(["return"]),
            gamepads={0: _pad(buttons=frozenset({GamepadButton.A}))},
        )
        actions = map_actions(raw, self.imap)
        # Action should appear exactly once (it's a set)
        self.assertIn("accept", actions)
        self.assertIsInstance(actions, frozenset)

    def test_neither_active_no_action(self):
        raw = _raw()
        self.assertNotIn("accept", map_actions(raw, self.imap))


# ---------------------------------------------------------------------------
# Empty map / edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_empty_input_map_returns_empty_actions(self):
        raw = _raw(frozenset(["space"]))
        self.assertEqual(map_actions(raw, InputMap.empty()), frozenset())

    def test_action_with_no_bindings_never_fires(self):
        imap = InputMap.empty().with_action("unused")
        raw  = _raw(frozenset(["space", "return"]))
        self.assertNotIn("unused", map_actions(raw, imap))

    def test_return_type_is_frozenset(self):
        result = map_actions(_raw(), InputMap.empty())
        self.assertIsInstance(result, frozenset)


if __name__ == "__main__":
    unittest.main()
