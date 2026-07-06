"""Tests for models.gamepad_state — GamepadButton, GamepadAxis, GamepadState."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire3d.models.gamepad_state import GamepadAxis, GamepadButton, GamepadState


class TestGamepadButton(unittest.TestCase):

    def test_all_buttons_have_string_values(self):
        for btn in GamepadButton:
            self.assertIsInstance(btn.value, str)

    def test_lookup_by_value(self):
        self.assertEqual(GamepadButton("a"), GamepadButton.A)
        self.assertEqual(GamepadButton("dpad_up"), GamepadButton.DPAD_UP)


class TestGamepadAxis(unittest.TestCase):

    def test_all_axes_have_string_values(self):
        for axis in GamepadAxis:
            self.assertIsInstance(axis.value, str)

    def test_lookup_by_value(self):
        self.assertEqual(GamepadAxis("left_x"), GamepadAxis.LEFT_X)
        self.assertEqual(GamepadAxis("right_trigger"), GamepadAxis.RIGHT_TRIGGER)


class TestGamepadState(unittest.TestCase):

    def _make_state(self) -> GamepadState:
        return GamepadState(
            pad_id=    0,
            connected= True,
            buttons=   frozenset({GamepadButton.A, GamepadButton.LB}),
            axes={
                GamepadAxis.LEFT_X:       0.5,
                GamepadAxis.LEFT_TRIGGER: -0.8,
            },
        )

    def test_is_button_pressed_true(self):
        state = self._make_state()
        self.assertTrue(state.is_button_pressed(GamepadButton.A))

    def test_is_button_pressed_false(self):
        state = self._make_state()
        self.assertFalse(state.is_button_pressed(GamepadButton.B))

    def test_get_axis_present(self):
        state = self._make_state()
        self.assertAlmostEqual(state.get_axis(GamepadAxis.LEFT_X), 0.5)

    def test_get_axis_absent_defaults_to_zero(self):
        state = self._make_state()
        self.assertEqual(state.get_axis(GamepadAxis.RIGHT_X), 0.0)

    def test_disconnected_factory(self):
        state = GamepadState.disconnected(2)
        self.assertEqual(state.pad_id, 2)
        self.assertFalse(state.connected)
        self.assertEqual(state.buttons, frozenset())
        self.assertEqual(state.axes, {})

    def test_round_trip_serialisation(self):
        original = self._make_state()
        restored = GamepadState.from_dict(original.to_dict())
        self.assertEqual(restored.pad_id, original.pad_id)
        self.assertEqual(restored.connected, original.connected)
        self.assertEqual(restored.buttons, original.buttons)
        self.assertAlmostEqual(
            restored.get_axis(GamepadAxis.LEFT_X),
            original.get_axis(GamepadAxis.LEFT_X),
        )

    def test_with_updates(self):
        state    = self._make_state()
        updated  = state.with_updates(connected=False)
        self.assertFalse(updated.connected)
        self.assertTrue(state.connected)  # original unchanged

    def test_immutable(self):
        state = self._make_state()
        with self.assertRaises(AttributeError):
            state.connected = False  # type: ignore[misc]


class TestGamepadStateDefaults(unittest.TestCase):

    def test_default_construction(self):
        state = GamepadState()
        self.assertEqual(state.pad_id, 0)
        self.assertFalse(state.connected)
        self.assertEqual(state.buttons, frozenset())
        self.assertEqual(state.axes, {})

    def test_from_dict_empty(self):
        state = GamepadState.from_dict({})
        self.assertEqual(state.pad_id, 0)
        self.assertFalse(state.connected)


if __name__ == "__main__":
    unittest.main()
