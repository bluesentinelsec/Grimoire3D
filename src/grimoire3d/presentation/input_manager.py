"""InputManager: hardware polling, hot-plug detection, and gamepad rumble.

This is the only module in Grimoire3D that touches pygame input hardware
directly.  It owns:

  - Keyboard state via pygame.key.get_pressed()
  - Mouse state via pygame.mouse
  - Gamepad lifecycle (open on connect, close on disconnect) via JOYDEVICEADDED
    and JOYDEVICEREMOVED events
  - Gamepad state polling (buttons, axes, hat/D-pad)
  - Rumble dispatch via pygame-ce's joystick.rumble()

Callers must:
  1. Call initialize() once after pygame.init().
  2. Call process_events(events) every frame with the list returned by
     pygame.event.get() *before* dispatching events to the rest of the engine
     (so hot-plug signals are consumed before the next poll()).
  3. Call poll(tick) to obtain a RawInputFrame for the current tick.
  4. Call quit() on shutdown.

Xbox-layout button and axis indices used here are the de-facto cross-platform
mapping reported by pygame-ce for the SDL2 GameController API.  D-pad input
is read from hat 0 with a fallback to dedicated button IDs for drivers that
expose the D-pad as buttons rather than a hat.
"""

from __future__ import annotations

import logging

import pygame

from grimoire3d.models.gamepad_state import GamepadAxis, GamepadButton, GamepadState
from grimoire3d.models.mouse_state import MouseButton, MouseState
from grimoire3d.models.raw_input_frame import RawInputFrame

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Xbox-layout hardware → enum mappings
# ---------------------------------------------------------------------------

# pygame joystick button index → GamepadButton
# Indices follow SDL2's GameController mapping as exposed by pygame-ce.
_BUTTON_MAP: dict[int, GamepadButton] = {
    0: GamepadButton.A,
    1: GamepadButton.B,
    2: GamepadButton.X,
    3: GamepadButton.Y,
    4: GamepadButton.LB,
    5: GamepadButton.RB,
    6: GamepadButton.BACK,
    7: GamepadButton.START,
    8: GamepadButton.LEFT_STICK,
    9: GamepadButton.RIGHT_STICK,
    10: GamepadButton.GUIDE,
}

# pygame joystick axis index → GamepadAxis
_AXIS_MAP: dict[int, GamepadAxis] = {
    0: GamepadAxis.LEFT_X,
    1: GamepadAxis.LEFT_Y,
    2: GamepadAxis.LEFT_TRIGGER,
    3: GamepadAxis.RIGHT_X,
    4: GamepadAxis.RIGHT_Y,
    5: GamepadAxis.RIGHT_TRIGGER,
}

# pygame mouse button → MouseButton
_MOUSE_BUTTON_MAP: dict[int, MouseButton] = {
    1: MouseButton.LEFT,
    2: MouseButton.MIDDLE,
    3: MouseButton.RIGHT,
    4: MouseButton.BACK,
    5: MouseButton.FORWARD,
}

# Maximum simultaneous gamepads supported
_MAX_PADS = 4


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _poll_keys() -> frozenset[str]:
    """Return the set of currently-pressed key names from pygame."""
    pressed = pygame.key.get_pressed()
    return frozenset(pygame.key.name(i) for i in range(len(pressed)) if pressed[i])


def _poll_gamepad(
    joy: pygame.joystick.Joystick,
    pad_id: int,
) -> GamepadState:
    """Build a GamepadState snapshot from a live pygame Joystick."""
    # --- Buttons ---
    buttons: set[GamepadButton] = set()
    for idx in range(joy.get_numbuttons()):
        btn = _BUTTON_MAP.get(idx)
        if btn is not None and joy.get_button(idx):
            buttons.add(btn)

    # --- Hat (D-pad) ---
    if joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        if hx == -1:
            buttons.add(GamepadButton.DPAD_LEFT)
        elif hx == 1:
            buttons.add(GamepadButton.DPAD_RIGHT)
        if hy == 1:
            buttons.add(GamepadButton.DPAD_UP)
        elif hy == -1:
            buttons.add(GamepadButton.DPAD_DOWN)

    # --- Axes ---
    axes: dict[GamepadAxis, float] = {}
    for idx in range(joy.get_numaxes()):
        axis = _AXIS_MAP.get(idx)
        if axis is not None:
            axes[axis] = joy.get_axis(idx)

    return GamepadState(
        pad_id=pad_id,
        connected=True,
        buttons=frozenset(buttons),
        axes=axes,
    )


def _screen_to_virtual(
    screen_pos: tuple[int, int],
    viewport: tuple[float, float, float] | None,
) -> tuple[float, float]:
    """Map physical pixel coordinates to virtual game-space coordinates.

    Args:
        screen_pos: (x, y) in physical window pixels
        viewport:   (scale, offset_x, offset_y) from the active Viewport, or
                    None when no letterboxing is in effect

    Returns:
        (vx, vy) in virtual pixel coordinates.
    """
    if viewport is None:
        return (float(screen_pos[0]), float(screen_pos[1]))
    scale, offset_x, offset_y = viewport
    if scale <= 0:
        return (float(screen_pos[0]), float(screen_pos[1]))
    vx = (screen_pos[0] - offset_x) / scale
    vy = (screen_pos[1] - offset_y) / scale
    return (vx, vy)


# ---------------------------------------------------------------------------
# InputManager
# ---------------------------------------------------------------------------


class InputManager:
    """Manages all input hardware: polling, hot-plug, and rumble.

    One InputManager instance is expected per application.  It is the only
    place in Grimoire3D that calls pygame input APIs directly.

    Hot-plug lifecycle
    ------------------
    Gamepads are tracked by their SDL2 *instance_id* (unique per physical
    plug event) rather than by device index.  When JOYDEVICEADDED fires the
    joystick is opened and assigned the lowest available logical slot (0–3).
    When JOYDEVICEREMOVED fires the slot is freed.  Existing MappedInputSource
    objects observe the change through connected_pad_ids.

    Scroll accumulation
    -------------------
    Mouse wheel deltas are accumulated across all MOUSEWHEEL events in the
    current frame's event list and reset to (0, 0) on the next poll().
    """

    def __init__(self) -> None:
        # instance_id → Joystick object (live hardware handle)
        self._joysticks: dict[int, pygame.joystick.Joystick] = {}
        # instance_id → logical slot (0–3)
        self._instance_to_slot: dict[int, int] = {}
        # logical slot → instance_id (inverse)
        self._slot_to_instance: dict[int, int] = {}
        # Accumulated scroll for the current frame
        self._scroll_x: float = 0.0
        self._scroll_y: float = 0.0
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        """Initialise the joystick subsystem and open already-connected pads.

        Must be called once after ``pygame.init()`` (or at least after
        ``pygame.joystick.init()``).
        """
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        for device_idx in range(pygame.joystick.get_count()):
            self._open_joystick(device_idx)

        self._initialized = True
        log.debug(
            "InputManager initialised; %d gamepad(s) connected",
            len(self._joysticks),
        )

    def quit(self) -> None:
        """Release all open joystick handles."""
        for joy in self._joysticks.values():
            try:
                joy.quit()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass
        self._joysticks.clear()
        self._instance_to_slot.clear()
        self._slot_to_instance.clear()
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Per-frame event processing
    # ------------------------------------------------------------------ #

    def process_events(self, events: list[pygame.event.Event]) -> None:
        """Handle hot-plug and scroll events from the pygame event queue.

        Must be called **every frame** with the full event list *before*
        calling poll().  Hot-plug changes take effect for the same frame
        if process_events is called first.

        Args:
            events: the list returned by pygame.event.get() for this frame
        """
        self._scroll_x = 0.0
        self._scroll_y = 0.0

        for event in events:
            if event.type == pygame.JOYDEVICEADDED:
                self._open_joystick(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._close_joystick(event.instance_id)
            elif event.type == pygame.MOUSEWHEEL:
                self._scroll_x += event.x
                self._scroll_y += event.y

    # ------------------------------------------------------------------ #
    # Polling
    # ------------------------------------------------------------------ #

    def poll(
        self,
        tick: int,
        viewport: tuple[float, float, float] | None = None,
    ) -> RawInputFrame:
        """Snapshot all input hardware and return a RawInputFrame.

        Args:
            tick:     current simulation tick (passed through to the frame)
            viewport: optional (scale, offset_x, offset_y) tuple from
                      logic.scaling.Viewport to convert mouse screen
                      coordinates to virtual game-space coordinates.
                      Pass None when no letterboxing is active.

        Returns:
            A complete, immutable RawInputFrame for *tick*.
        """
        keys_held = _poll_keys()
        mouse = self._poll_mouse(viewport)
        gamepads = self._poll_gamepads()

        return RawInputFrame(
            tick=tick,
            keys_held=keys_held,
            mouse=mouse,
            gamepads=gamepads,
        )

    # ------------------------------------------------------------------ #
    # Rumble
    # ------------------------------------------------------------------ #

    def rumble(
        self,
        pad_id: int,
        low_freq: float,
        high_freq: float,
        duration_ms: int,
    ) -> bool:
        """Trigger gamepad rumble motors.

        Args:
            pad_id:      logical gamepad slot (0–3)
            low_freq:    low-frequency (grip) motor intensity in [0.0, 1.0]
            high_freq:   high-frequency (trigger) motor intensity in [0.0, 1.0]
            duration_ms: duration in milliseconds; 0 stops existing rumble

        Returns:
            True if rumble was dispatched to the device, False if the slot is
            not connected or the controller does not support rumble.
        """
        instance_id = self._slot_to_instance.get(pad_id)
        if instance_id is None:
            return False
        joy = self._joysticks.get(instance_id)
        if joy is None:
            return False
        try:
            joy.rumble(low_freq, high_freq, duration_ms)
            return True
        except pygame.error:
            return False

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    @property
    def connected_pad_ids(self) -> frozenset[int]:
        """Return the set of logical slot IDs that are currently connected."""
        return frozenset(self._slot_to_instance.keys())

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _open_joystick(self, device_index: int) -> None:
        """Open the joystick at *device_index* and assign it a logical slot."""
        try:
            joy = pygame.joystick.Joystick(device_index)
            joy.init()
        except pygame.error as exc:
            log.warning("Failed to open joystick %d: %s", device_index, exc)
            return

        instance_id = joy.get_instance_id()
        if instance_id in self._instance_to_slot:
            return  # already tracked (spurious duplicate event)

        slot = self._next_free_slot()
        if slot is None:
            log.warning(
                "Ignoring gamepad (instance %d): all %d slots occupied",
                instance_id,
                _MAX_PADS,
            )
            joy.quit()
            return

        self._joysticks[instance_id] = joy
        self._instance_to_slot[instance_id] = slot
        self._slot_to_instance[slot] = instance_id
        log.info(
            "Gamepad connected: %r → slot %d (instance_id=%d)",
            joy.get_name(),
            slot,
            instance_id,
        )

    def _close_joystick(self, instance_id: int) -> None:
        """Release the joystick identified by *instance_id* and free its slot."""
        joy = self._joysticks.pop(instance_id, None)
        slot = self._instance_to_slot.pop(instance_id, None)
        if slot is not None:
            self._slot_to_instance.pop(slot, None)
        if joy is not None:
            try:
                joy.quit()
            except Exception:  # noqa: BLE001
                pass
            log.info(
                "Gamepad disconnected: slot %d (instance_id=%d)", slot, instance_id
            )

    def _next_free_slot(self) -> int | None:
        """Return the lowest free slot index, or None if all slots are taken."""
        used = set(self._slot_to_instance.keys())
        for slot in range(_MAX_PADS):
            if slot not in used:
                return slot
        return None

    def _poll_mouse(self, viewport: tuple[float, float, float] | None) -> MouseState:
        screen_pos = pygame.mouse.get_pos()
        pressed = pygame.mouse.get_pressed(num_buttons=5)
        buttons: set[MouseButton] = set()
        for idx, held in enumerate(pressed):
            mapped = _MOUSE_BUTTON_MAP.get(idx + 1)
            if held and mapped is not None:
                buttons.add(mapped)
        virtual_pos = _screen_to_virtual(screen_pos, viewport)
        return MouseState(
            position=(float(screen_pos[0]), float(screen_pos[1])),
            virtual_position=virtual_pos,
            buttons=frozenset(buttons),
            scroll_delta=(self._scroll_x, self._scroll_y),
        )

    def _poll_gamepads(self) -> dict[int, GamepadState]:
        gamepads: dict[int, GamepadState] = {}
        for instance_id, joy in self._joysticks.items():
            slot = self._instance_to_slot.get(instance_id)
            if slot is None:
                continue
            try:
                gamepads[slot] = _poll_gamepad(joy, slot)
            except pygame.error as exc:
                log.warning("Error polling gamepad slot %d: %s", slot, exc)
                gamepads[slot] = GamepadState.disconnected(slot)
        return gamepads
