"""Tests for presentation.mapped_input_source — MappedInputSource."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire3d.models.gamepad_state import GamepadButton, GamepadState
from grimoire3d.models.input_binding import GamepadButtonBinding, KeyBinding
from grimoire3d.models.input_frame import InputFrame
from grimoire3d.models.input_map import InputMap
from grimoire3d.models.mouse_state import MouseState
from grimoire3d.models.raw_input_frame import RawInputFrame
from grimoire3d.presentation.mapped_input_source import MappedInputSource


def _raw(keys: frozenset[str] = frozenset(),
         gamepads: dict | None = None) -> RawInputFrame:
    return RawInputFrame(
        tick=      0,
        keys_held= keys,
        mouse=     MouseState(),
        gamepads=  gamepads or {},
    )


def _imap() -> InputMap:
    return (
        InputMap.empty()
        .with_binding("jump",   KeyBinding("space"))
        .with_binding("accept", GamepadButtonBinding(GamepadButton.A))
    )


class TestMappedInputSourceBasic(unittest.TestCase):

    def test_player_id(self):
        src = MappedInputSource("P1", _imap())
        self.assertEqual(src.player_id, "P1")

    def test_poll_no_raw_returns_empty_frame(self):
        src   = MappedInputSource("P1", _imap())
        frame = src.poll(tick=1)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.actions, frozenset())
        self.assertEqual(frame.tick, 1)

    def test_poll_with_key_pressed(self):
        src = MappedInputSource("P1", _imap())
        src.update_raw(_raw(frozenset(["space"])))
        frame = src.poll(tick=2)
        self.assertIn("jump", frame.actions)

    def test_poll_returns_input_frame(self):
        src   = MappedInputSource("P1", _imap())
        src.update_raw(_raw())
        frame = src.poll(tick=0)
        self.assertIsInstance(frame, InputFrame)

    def test_player_id_in_frame(self):
        src = MappedInputSource("P2", _imap())
        src.update_raw(_raw())
        frame = src.poll(tick=0)
        self.assertEqual(frame.player_id, "P2")

    def test_tick_propagated(self):
        src = MappedInputSource("P1", _imap())
        src.update_raw(_raw())
        self.assertEqual(src.poll(tick=42).tick, 42)


class TestMappedInputSourceRequirePad(unittest.TestCase):

    def _connected_pad(self) -> GamepadState:
        return GamepadState(pad_id=0, connected=True,
                            buttons=frozenset({GamepadButton.A}))

    def _disconnected_pad(self) -> GamepadState:
        return GamepadState(pad_id=0, connected=False)

    def test_require_pad_connected_returns_frame(self):
        src = MappedInputSource("P1", _imap(), pad_id=0, require_pad=True)
        src.update_raw(_raw(gamepads={0: self._connected_pad()}))
        frame = src.poll(tick=0)
        self.assertIsNotNone(frame)

    def test_require_pad_disconnected_returns_none(self):
        src = MappedInputSource("P1", _imap(), pad_id=0, require_pad=True)
        src.update_raw(_raw(gamepads={0: self._disconnected_pad()}))
        self.assertIsNone(src.poll(tick=0))

    def test_no_require_pad_disconnected_returns_empty_frame(self):
        src = MappedInputSource("P1", _imap(), pad_id=0, require_pad=False)
        src.update_raw(_raw(gamepads={0: self._disconnected_pad()}))
        frame = src.poll(tick=0)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.actions, frozenset())


class TestMappedInputSourcePadIdFilter(unittest.TestCase):

    def test_pad_id_filters_gamepad_bindings(self):
        imap = InputMap.empty().with_binding(
            "accept", GamepadButtonBinding(GamepadButton.A)
        )
        pad0 = GamepadState(pad_id=0, connected=True, buttons=frozenset())
        pad1 = GamepadState(pad_id=1, connected=True,
                            buttons=frozenset({GamepadButton.A}))
        src = MappedInputSource("P2", imap, pad_id=1)
        src.update_raw(_raw(gamepads={0: pad0, 1: pad1}))
        frame = src.poll(tick=0)
        self.assertIn("accept", frame.actions)

    def test_wrong_pad_id_no_action(self):
        imap = InputMap.empty().with_binding(
            "accept", GamepadButtonBinding(GamepadButton.A)
        )
        pad0 = GamepadState(pad_id=0, connected=True,
                            buttons=frozenset({GamepadButton.A}))
        src = MappedInputSource("P2", imap, pad_id=1)  # slot 1, but A is on slot 0
        src.update_raw(_raw(gamepads={0: pad0}))
        frame = src.poll(tick=0)
        self.assertNotIn("accept", frame.actions)


class TestMappedInputSourceSetInputMap(unittest.TestCase):

    def test_hot_swap_input_map(self):
        src  = MappedInputSource("P1", _imap())
        src.update_raw(_raw(frozenset(["space"])))
        self.assertIn("jump", src.poll(tick=0).actions)

        new_map = InputMap.empty().with_binding("fire", KeyBinding("space"))
        src.set_input_map(new_map)
        frame = src.poll(tick=1)
        self.assertNotIn("jump", frame.actions)
        self.assertIn("fire",    frame.actions)

    def test_input_map_property(self):
        imap = _imap()
        src  = MappedInputSource("P1", imap)
        self.assertIs(src.input_map, imap)


if __name__ == "__main__":
    unittest.main()
