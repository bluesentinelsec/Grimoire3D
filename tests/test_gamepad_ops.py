"""Tests for logic.gamepad_ops — pure gamepad math helpers."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire2d.models.gamepad_state import GamepadAxis, GamepadButton, GamepadState
from grimoire2d.logic.gamepad_ops import (
    deadzone,
    get_stick_vector,
    is_axis_pressed,
    trigger_value,
)


class TestDeadzone(unittest.TestCase):

    def test_inner_snaps_to_zero(self):
        self.assertEqual(deadzone(0.05), 0.0)
        self.assertEqual(deadzone(-0.05), 0.0)

    def test_outer_snaps_to_one(self):
        self.assertAlmostEqual(deadzone(0.96), 1.0)
        self.assertAlmostEqual(deadzone(-0.96), -1.0)

    def test_midrange_remapped(self):
        val = deadzone(0.5, inner=0.1, outer=0.9)
        self.assertGreater(val, 0.0)
        self.assertLess(val, 1.0)

    def test_zero_is_in_deadzone(self):
        self.assertEqual(deadzone(0.0), 0.0)

    def test_sign_preserved(self):
        pos = deadzone(0.5)
        neg = deadzone(-0.5)
        self.assertGreater(pos, 0.0)
        self.assertLess(neg, 0.0)
        self.assertAlmostEqual(abs(pos), abs(neg))

    def test_custom_inner_outer(self):
        self.assertEqual(deadzone(0.05, inner=0.1, outer=0.9), 0.0)
        self.assertAlmostEqual(deadzone(0.91, inner=0.1, outer=0.9), 1.0)


class TestGetStickVector(unittest.TestCase):

    def _state(self, lx: float, ly: float) -> GamepadState:
        return GamepadState(
            connected= True,
            axes={
                GamepadAxis.LEFT_X: lx,
                GamepadAxis.LEFT_Y: ly,
            },
        )

    def test_y_inversion(self):
        # pygame reports -1 as "up"; we should return +y for up
        _, y = get_stick_vector(
            self._state(0.0, -1.0),
            GamepadAxis.LEFT_X,
            GamepadAxis.LEFT_Y,
        )
        self.assertAlmostEqual(y, 1.0)

    def test_neutral_returns_zero_vector(self):
        x, y = get_stick_vector(
            self._state(0.0, 0.0),
            GamepadAxis.LEFT_X,
            GamepadAxis.LEFT_Y,
        )
        self.assertEqual(x, 0.0)
        self.assertEqual(y, 0.0)

    def test_small_input_clipped_by_inner_deadzone(self):
        x, y = get_stick_vector(
            self._state(0.05, 0.05),
            GamepadAxis.LEFT_X,
            GamepadAxis.LEFT_Y,
        )
        self.assertEqual(x, 0.0)
        self.assertEqual(y, 0.0)

    def test_full_right(self):
        x, _ = get_stick_vector(
            self._state(1.0, 0.0),
            GamepadAxis.LEFT_X,
            GamepadAxis.LEFT_Y,
        )
        self.assertAlmostEqual(x, 1.0)


class TestTriggerValue(unittest.TestCase):

    def _state(self, axis: GamepadAxis, value: float) -> GamepadState:
        return GamepadState(connected=True, axes={axis: value})

    def test_released_trigger_returns_zero(self):
        state = self._state(GamepadAxis.LEFT_TRIGGER, -1.0)
        self.assertAlmostEqual(trigger_value(state, GamepadAxis.LEFT_TRIGGER), 0.0)

    def test_fully_pressed_trigger_returns_one(self):
        state = self._state(GamepadAxis.LEFT_TRIGGER, 1.0)
        self.assertAlmostEqual(trigger_value(state, GamepadAxis.LEFT_TRIGGER), 1.0)

    def test_half_pressed(self):
        state = self._state(GamepadAxis.RIGHT_TRIGGER, 0.0)
        self.assertAlmostEqual(trigger_value(state, GamepadAxis.RIGHT_TRIGGER), 0.5)


class TestIsAxisPressed(unittest.TestCase):

    def _state(self, axis: GamepadAxis, value: float) -> GamepadState:
        return GamepadState(connected=True, axes={axis: value})

    def test_positive_direction_above_threshold(self):
        state = self._state(GamepadAxis.LEFT_X, 0.8)
        self.assertTrue(is_axis_pressed(state, GamepadAxis.LEFT_X, direction=1))

    def test_positive_direction_below_threshold(self):
        state = self._state(GamepadAxis.LEFT_X, 0.3)
        self.assertFalse(is_axis_pressed(state, GamepadAxis.LEFT_X, direction=1))

    def test_negative_direction_above_threshold(self):
        state = self._state(GamepadAxis.LEFT_X, -0.8)
        self.assertTrue(is_axis_pressed(state, GamepadAxis.LEFT_X, direction=-1))

    def test_negative_direction_below_threshold(self):
        state = self._state(GamepadAxis.LEFT_X, -0.3)
        self.assertFalse(is_axis_pressed(state, GamepadAxis.LEFT_X, direction=-1))

    def test_exactly_at_threshold_is_pressed(self):
        state = self._state(GamepadAxis.LEFT_X, 0.5)
        self.assertTrue(is_axis_pressed(state, GamepadAxis.LEFT_X, direction=1, threshold=0.5))

    def test_missing_axis_defaults_to_not_pressed(self):
        state = GamepadState(connected=True)  # no axes
        self.assertFalse(is_axis_pressed(state, GamepadAxis.RIGHT_X))

    def test_custom_threshold(self):
        state = self._state(GamepadAxis.LEFT_TRIGGER, 0.2)
        self.assertTrue(is_axis_pressed(state, GamepadAxis.LEFT_TRIGGER, direction=1, threshold=0.1))
        self.assertFalse(is_axis_pressed(state, GamepadAxis.LEFT_TRIGGER, direction=1, threshold=0.5))


if __name__ == "__main__":
    unittest.main()
