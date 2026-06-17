"""Tests for models.raw_input_frame — RawInputFrame construction and serialisation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire2d.models.gamepad_state import GamepadAxis, GamepadButton, GamepadState
from grimoire2d.models.mouse_state import MouseButton, MouseState
from grimoire2d.models.raw_input_frame import RawInputFrame


class TestRawInputFrameDefaults(unittest.TestCase):

    def test_default_construction(self):
        frame = RawInputFrame()
        self.assertEqual(frame.tick, 0)
        self.assertEqual(frame.keys_held, frozenset())
        self.assertEqual(frame.gamepads, {})

    def test_get_pad_absent_returns_disconnected_sentinel(self):
        frame = RawInputFrame()
        pad = frame.get_pad(0)
        self.assertFalse(pad.connected)
        self.assertEqual(pad.pad_id, 0)


class TestRawInputFrameConstruction(unittest.TestCase):

    def _make_frame(self) -> RawInputFrame:
        pad0 = GamepadState(
            pad_id=    0,
            connected= True,
            buttons=   frozenset({GamepadButton.A}),
            axes=      {GamepadAxis.LEFT_X: 0.75},
        )
        mouse = MouseState(
            position=     (320.0, 240.0),
            buttons=      frozenset({MouseButton.LEFT}),
            scroll_delta= (0.0, 1.0),
        )
        return RawInputFrame(
            tick=      5,
            keys_held= frozenset({"space", "left"}),
            mouse=     mouse,
            gamepads=  {0: pad0},
        )

    def test_tick(self):
        self.assertEqual(self._make_frame().tick, 5)

    def test_keys_held(self):
        frame = self._make_frame()
        self.assertIn("space", frame.keys_held)
        self.assertIn("left",  frame.keys_held)

    def test_get_pad_connected(self):
        pad = self._make_frame().get_pad(0)
        self.assertTrue(pad.connected)
        self.assertIn(GamepadButton.A, pad.buttons)

    def test_get_pad_missing_slot_returns_sentinel(self):
        pad = self._make_frame().get_pad(3)
        self.assertFalse(pad.connected)
        self.assertEqual(pad.pad_id, 3)

    def test_mouse_state(self):
        mouse = self._make_frame().mouse
        self.assertIn(MouseButton.LEFT, mouse.buttons)
        self.assertAlmostEqual(mouse.position[0], 320.0)


class TestRawInputFrameSerialisation(unittest.TestCase):

    def _make_frame(self) -> RawInputFrame:
        pad = GamepadState(
            pad_id=    1,
            connected= True,
            buttons=   frozenset({GamepadButton.B}),
            axes=      {GamepadAxis.RIGHT_X: -0.5},
        )
        return RawInputFrame(
            tick=      10,
            keys_held= frozenset({"a", "d"}),
            gamepads=  {1: pad},
        )

    def test_round_trip(self):
        original = self._make_frame()
        restored = RawInputFrame.from_dict(original.to_dict())
        self.assertEqual(restored.tick, original.tick)
        self.assertEqual(restored.keys_held, original.keys_held)
        self.assertIn(1, restored.gamepads)
        pad = restored.gamepads[1]
        self.assertTrue(pad.connected)
        self.assertIn(GamepadButton.B, pad.buttons)
        self.assertAlmostEqual(pad.get_axis(GamepadAxis.RIGHT_X), -0.5)

    def test_from_dict_empty(self):
        frame = RawInputFrame.from_dict({})
        self.assertEqual(frame.tick, 0)
        self.assertEqual(frame.keys_held, frozenset())
        self.assertEqual(frame.gamepads, {})

    def test_with_updates(self):
        frame   = self._make_frame()
        updated = frame.with_updates(tick=99)
        self.assertEqual(updated.tick, 99)
        self.assertEqual(frame.tick, 10)  # original unchanged


if __name__ == "__main__":
    unittest.main()
