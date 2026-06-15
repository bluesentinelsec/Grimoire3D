"""Tests for models.input_map — InputMap construction, mutation, and serialisation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire2d.models.input_binding import (
    GamepadAxisBinding,
    GamepadButtonBinding,
    KeyBinding,
    MouseButtonBinding,
)
from grimoire2d.models.gamepad_state import GamepadAxis, GamepadButton
from grimoire2d.models.input_map import InputMap


class TestInputMapConstruction(unittest.TestCase):

    def test_empty_factory(self):
        imap = InputMap.empty()
        self.assertEqual(imap.actions, {})

    def test_has_action_false_on_empty(self):
        self.assertFalse(InputMap.empty().has_action("jump"))

    def test_action_names_empty(self):
        self.assertEqual(InputMap.empty().action_names(), frozenset())


class TestInputMapWithBinding(unittest.TestCase):

    def test_add_key_binding(self):
        imap = InputMap.empty().with_binding("jump", KeyBinding("space"))
        self.assertIn(KeyBinding("space"), imap.get_bindings("jump"))

    def test_add_multiple_bindings_same_action(self):
        imap = (
            InputMap.empty()
            .with_binding("accept", KeyBinding("return"))
            .with_binding("accept", GamepadButtonBinding(GamepadButton.A))
        )
        bindings = imap.get_bindings("accept")
        self.assertIn(KeyBinding("return"), bindings)
        self.assertIn(GamepadButtonBinding(GamepadButton.A), bindings)
        self.assertEqual(len(bindings), 2)

    def test_add_binding_does_not_mutate_original(self):
        original = InputMap.empty()
        _updated = original.with_binding("fire", KeyBinding("z"))
        self.assertFalse(original.has_action("fire"))

    def test_duplicate_binding_is_idempotent(self):
        b = KeyBinding("space")
        imap = InputMap.empty().with_binding("jump", b).with_binding("jump", b)
        self.assertEqual(len(imap.get_bindings("jump")), 1)

    def test_get_bindings_unknown_action_returns_empty(self):
        self.assertEqual(InputMap.empty().get_bindings("nonexistent"), frozenset())


class TestInputMapWithoutBinding(unittest.TestCase):

    def test_remove_existing_binding(self):
        b = KeyBinding("space")
        imap = InputMap.empty().with_binding("jump", b).without_binding("jump", b)
        self.assertNotIn(b, imap.get_bindings("jump"))

    def test_remove_nonexistent_binding_is_safe(self):
        imap = InputMap.empty().with_binding("jump", KeyBinding("space"))
        result = imap.without_binding("jump", KeyBinding("x"))
        self.assertIn(KeyBinding("space"), result.get_bindings("jump"))


class TestInputMapWithoutAction(unittest.TestCase):

    def test_remove_action(self):
        imap = InputMap.empty().with_binding("fire", KeyBinding("z"))
        result = imap.without_action("fire")
        self.assertFalse(result.has_action("fire"))

    def test_remove_nonexistent_action_is_safe(self):
        imap = InputMap.empty()
        result = imap.without_action("nonexistent")
        self.assertEqual(result.action_names(), frozenset())


class TestInputMapWithAction(unittest.TestCase):

    def test_define_action_no_bindings(self):
        imap = InputMap.empty().with_action("ui_cancel")
        self.assertTrue(imap.has_action("ui_cancel"))
        self.assertEqual(imap.get_bindings("ui_cancel"), frozenset())

    def test_define_action_with_bindings(self):
        b = KeyBinding("escape")
        imap = InputMap.empty().with_action("ui_cancel", frozenset({b}))
        self.assertIn(b, imap.get_bindings("ui_cancel"))


class TestInputMapSerialisation(unittest.TestCase):

    def _complex_map(self) -> InputMap:
        return (
            InputMap.empty()
            .with_binding("accept", KeyBinding("return"))
            .with_binding("accept", GamepadButtonBinding(GamepadButton.A))
            .with_binding("cancel", KeyBinding("escape"))
            .with_binding("cancel", GamepadButtonBinding(GamepadButton.B))
            .with_binding("fire",   MouseButtonBinding(1))
            .with_binding("aim",    GamepadAxisBinding(GamepadAxis.RIGHT_X))
        )

    def test_to_dict_has_expected_keys(self):
        d = self._complex_map().to_dict()
        self.assertIn("actions", d)
        self.assertIn("version", d)

    def test_round_trip(self):
        original = self._complex_map()
        restored = InputMap.from_dict(original.to_dict())
        for action in original.action_names():
            self.assertEqual(
                restored.get_bindings(action),
                original.get_bindings(action),
                msg=f"Mismatch for action: {action!r}",
            )

    def test_from_dict_empty(self):
        imap = InputMap.from_dict({})
        self.assertEqual(imap.actions, {})

    def test_action_names(self):
        imap = self._complex_map()
        self.assertEqual(imap.action_names(), frozenset({"accept", "cancel", "fire", "aim"}))


if __name__ == "__main__":
    unittest.main()
