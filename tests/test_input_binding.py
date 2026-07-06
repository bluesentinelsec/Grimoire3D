"""Tests for models.input_binding — binding types and InputBinding union."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire3d.models.input_binding import (
    GamepadAxisBinding,
    GamepadButtonBinding,
    InputBinding,
    KeyBinding,
    MouseButtonBinding,
)
from grimoire3d.models.gamepad_state import GamepadAxis, GamepadButton


class TestKeyBinding(unittest.TestCase):

    def test_construction(self):
        b = KeyBinding("space")
        self.assertEqual(b.key, "space")

    def test_equality(self):
        self.assertEqual(KeyBinding("a"), KeyBinding("a"))
        self.assertNotEqual(KeyBinding("a"), KeyBinding("b"))

    def test_hashable_for_frozenset(self):
        s = frozenset({KeyBinding("a"), KeyBinding("a"), KeyBinding("b")})
        self.assertEqual(len(s), 2)

    def test_immutable(self):
        b = KeyBinding("x")
        with self.assertRaises(AttributeError):
            b.key = "y"  # type: ignore[misc]


class TestMouseButtonBinding(unittest.TestCase):

    def test_construction(self):
        b = MouseButtonBinding(1)
        self.assertEqual(b.button, 1)

    def test_equality(self):
        self.assertEqual(MouseButtonBinding(1), MouseButtonBinding(1))
        self.assertNotEqual(MouseButtonBinding(1), MouseButtonBinding(2))

    def test_hashable(self):
        s = frozenset({MouseButtonBinding(1), MouseButtonBinding(1)})
        self.assertEqual(len(s), 1)


class TestGamepadButtonBinding(unittest.TestCase):

    def test_construction(self):
        b = GamepadButtonBinding(GamepadButton.A)
        self.assertEqual(b.button, GamepadButton.A)

    def test_equality(self):
        self.assertEqual(
            GamepadButtonBinding(GamepadButton.A),
            GamepadButtonBinding(GamepadButton.A),
        )
        self.assertNotEqual(
            GamepadButtonBinding(GamepadButton.A),
            GamepadButtonBinding(GamepadButton.B),
        )

    def test_hashable(self):
        s = frozenset({
            GamepadButtonBinding(GamepadButton.A),
            GamepadButtonBinding(GamepadButton.B),
        })
        self.assertEqual(len(s), 2)


class TestGamepadAxisBinding(unittest.TestCase):

    def test_defaults(self):
        b = GamepadAxisBinding(GamepadAxis.LEFT_X)
        self.assertEqual(b.direction, 1)
        self.assertAlmostEqual(b.threshold, 0.5)

    def test_custom_values(self):
        b = GamepadAxisBinding(GamepadAxis.LEFT_TRIGGER, direction=1, threshold=0.1)
        self.assertEqual(b.axis, GamepadAxis.LEFT_TRIGGER)
        self.assertEqual(b.direction, 1)
        self.assertAlmostEqual(b.threshold, 0.1)

    def test_negative_direction(self):
        b = GamepadAxisBinding(GamepadAxis.LEFT_X, direction=-1)
        self.assertEqual(b.direction, -1)

    def test_hashable(self):
        b1 = GamepadAxisBinding(GamepadAxis.LEFT_X,  direction=1)
        b2 = GamepadAxisBinding(GamepadAxis.LEFT_X,  direction=-1)
        b3 = GamepadAxisBinding(GamepadAxis.RIGHT_X, direction=1)
        s = frozenset({b1, b2, b3})
        self.assertEqual(len(s), 3)


class TestInputBindingUnion(unittest.TestCase):

    def test_all_types_accepted_in_union_collection(self):
        bindings: list[InputBinding] = [
            KeyBinding("space"),
            MouseButtonBinding(1),
            GamepadButtonBinding(GamepadButton.A),
            GamepadAxisBinding(GamepadAxis.LEFT_X),
        ]
        self.assertEqual(len(bindings), 4)

    def test_mixed_frozenset(self):
        s: frozenset[InputBinding] = frozenset({
            KeyBinding("jump"),
            GamepadButtonBinding(GamepadButton.A),
        })
        self.assertEqual(len(s), 2)


if __name__ == "__main__":
    unittest.main()
