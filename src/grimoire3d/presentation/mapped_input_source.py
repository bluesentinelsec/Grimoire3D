"""MappedInputSource: bridges InputManager + InputMap → InputSource protocol.

This class is the standard way to wire the hardware layer into the
simulation's InputSource pipeline.  One MappedInputSource per player;
each can be bound to a specific gamepad slot or left unbound (accepts
input from any connected pad or keyboard/mouse only).

When the assigned pad is disconnected the source returns None, signalling
to route_inputs() that no frame is available for this player this tick.
The game loop can use connected_pad_ids from the InputManager to detect
the disconnection and display a reconnect prompt.
"""

from __future__ import annotations

from grimoire3d.models.input_frame import InputFrame
from grimoire3d.models.input_map import InputMap
from grimoire3d.models.raw_input_frame import RawInputFrame
from grimoire3d.logic.input_mapper import map_actions


class MappedInputSource:
    """Polls the InputManager for one player and maps hardware state to actions.

    Implements the InputSource protocol defined in logic.input_router so it
    can be passed directly to route_inputs() alongside network sources,
    AI stubs, or replay sources.

    Args:
        player_id:  the player this source drives (matches InputFrame.player_id)
        input_map:  the action→binding configuration for this player
        pad_id:     restrict gamepad binding resolution to this logical slot;
                    None means any connected gamepad satisfies gamepad bindings
        require_pad: when True and pad_id is given, poll() returns None while
                     the pad is disconnected (signals "waiting for reconnect")
    """

    def __init__(
        self,
        player_id: str,
        input_map: InputMap,
        pad_id: int | None = None,
        require_pad: bool = False,
    ) -> None:
        self._player_id = player_id
        self._input_map = input_map
        self._pad_id = pad_id
        self._require_pad = require_pad
        # Raw frame is injected by the game loop before each call to poll().
        # This avoids InputManager being a direct dependency here (testable).
        self._raw: RawInputFrame | None = None

    # ------------------------------------------------------------------ #
    # InputSource protocol
    # ------------------------------------------------------------------ #

    @property
    def player_id(self) -> str:
        return self._player_id

    def poll(self, tick: int) -> InputFrame | None:
        """Return an InputFrame for *tick*, or None if the required pad is absent.

        Before calling poll() each frame, supply the current hardware snapshot
        via update_raw().  If update_raw() has never been called, an empty
        frame is returned.
        """
        raw = self._raw
        if raw is None:
            return InputFrame.empty(self._player_id, tick)

        if self._require_pad and self._pad_id is not None:
            pad = raw.get_pad(self._pad_id)
            if not pad.connected:
                return None

        actions = map_actions(raw, self._input_map, self._pad_id)
        return InputFrame(
            player_id=self._player_id,
            tick=tick,
            actions=actions,
        )

    # ------------------------------------------------------------------ #
    # Runtime configuration
    # ------------------------------------------------------------------ #

    def update_raw(self, raw: RawInputFrame) -> None:
        """Inject the current hardware snapshot before calling poll().

        Typical usage in a game loop::

            raw = input_manager.poll(tick)
            for source in mapped_sources:
                source.update_raw(raw)
            frames = route_inputs(mapped_sources, tick)
        """
        self._raw = raw

    def set_input_map(self, input_map: InputMap) -> None:
        """Hot-swap the binding configuration (e.g. after user reconfigures keys)."""
        self._input_map = input_map

    @property
    def input_map(self) -> InputMap:
        return self._input_map

    @property
    def pad_id(self) -> int | None:
        return self._pad_id
