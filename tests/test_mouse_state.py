"""Tests for models.mouse_state — MouseButton, MouseState."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire2d.models.mouse_state import MouseButton, MouseState


class TestMouseButton(unittest.TestCase):

    def test_all_buttons_have_string_values(self):
        for btn in MouseButton:
            self.assertIsInstance(btn.value, str)

    def test_lookup_by_value(self):
        self.assertEqual(MouseButton("left"),    MouseButton.LEFT)
        self.assertEqual(MouseButton("forward"), MouseButton.FORWARD)


class TestMouseState(unittest.TestCase):

    def _make_state(self) -> MouseState:
        return MouseState(
            position=         (100.0, 200.0),
            virtual_position= (50.0,  100.0),
            buttons=          frozenset({MouseButton.LEFT}),
            scroll_delta=     (0.0, 2.0),
        )

    def test_is_button_pressed_true(self):
        self.assertTrue(self._make_state().is_button_pressed(MouseButton.LEFT))

    def test_is_button_pressed_false(self):
        self.assertFalse(self._make_state().is_button_pressed(MouseButton.RIGHT))

    def test_default_construction(self):
        state = MouseState()
        self.assertEqual(state.position,         (0.0, 0.0))
        self.assertEqual(state.virtual_position, (0.0, 0.0))
        self.assertEqual(state.buttons,          frozenset())
        self.assertEqual(state.scroll_delta,     (0.0, 0.0))

    def test_round_trip_serialisation(self):
        original = self._make_state()
        restored = MouseState.from_dict(original.to_dict())
        self.assertAlmostEqual(restored.position[0], original.position[0])
        self.assertAlmostEqual(restored.position[1], original.position[1])
        self.assertAlmostEqual(restored.virtual_position[0], original.virtual_position[0])
        self.assertEqual(restored.buttons, original.buttons)
        self.assertAlmostEqual(restored.scroll_delta[1], original.scroll_delta[1])

    def test_with_updates(self):
        original = self._make_state()
        updated  = original.with_updates(scroll_delta=(1.0, -1.0))
        self.assertEqual(updated.scroll_delta, (1.0, -1.0))
        self.assertEqual(original.scroll_delta, (0.0, 2.0))  # unchanged

    def test_immutable(self):
        state = self._make_state()
        with self.assertRaises(AttributeError):
            state.position = (0.0, 0.0)  # type: ignore[misc]

    def test_from_dict_empty(self):
        state = MouseState.from_dict({})
        self.assertEqual(state.position,     (0.0, 0.0))
        self.assertEqual(state.scroll_delta, (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
