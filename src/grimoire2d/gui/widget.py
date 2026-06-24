"""Base Widget class for the in-house GUI library.

Widgets are retained objects with layout information. They draw
themselves using the engine's Renderer and receive input dispatched
from a GUIManager.

Key design goals:
- Tkinter-like grid layout (no hard-coded pixel positions for most use).
- Correct nesting, clipping, focus, hover/active states.
- Works with the engine's virtual resolution, resize, and split-screen
  (by rendering a GUI subtree clipped to a viewport).
- All coordinates are in virtual space.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .gui import GUIManager


@dataclass
class GridOptions:
    """Options for .grid() placement, mirroring tkinter.grid() subset."""

    row: int = 0
    column: int = 0
    rowspan: int = 1
    columnspan: int = 1
    sticky: str = ""  # combination of 'n','s','e','w'
    padx: int = 0
    pady: int = 0
    ipadx: int = 0
    ipady: int = 0


class Widget:
    """Base class for all GUI elements.

    A widget has:
    - A parent (for tree structure and layout)
    - Children
    - Layout information (after grid())
    - Computed rectangle after layout
    - State (hovered, pressed, focused, disabled)
    - Ability to draw and handle events
    """

    def __init__(self, parent: Optional[Widget] = None, **kwargs: Any) -> None:
        self.parent: Optional[Widget] = parent
        self.children: list[Widget] = []
        self.grid_options: Optional[GridOptions] = None
        self.x: float = 0.0
        self.y: float = 0.0
        self.width: float = 0.0
        self.height: float = 0.0
        self._hovered = False
        self._pressed = False
        self._focused = False
        self._disabled = False
        self._visible = True

        if parent is not None:
            parent.children.append(self)

        # Optional user data
        self.user_data: dict[str, Any] = {}

    def grid(
        self,
        row: int = 0,
        column: int = 0,
        rowspan: int = 1,
        columnspan: int = 1,
        sticky: str = "",
        padx: int = 0,
        pady: int = 0,
        ipadx: int = 0,
        ipady: int = 0,
    ) -> None:
        """Place this widget using a grid layout (Tkinter-like).

        Must be called on a widget whose parent supports grid layout
        (typically a Frame that uses GridLayout).
        """
        self.grid_options = GridOptions(
            row=row,
            column=column,
            rowspan=rowspan,
            columnspan=columnspan,
            sticky=sticky,
            padx=padx,
            pady=pady,
            ipadx=ipadx,
            ipady=ipady,
        )

    def destroy(self) -> None:
        """Remove from parent and clear children."""
        if self.parent is not None and self in self.parent.children:
            self.parent.children.remove(self)
        for child in list(self.children):
            child.destroy()
        self.children.clear()
        self.parent = None

    # --- Sizing (to be overridden by concrete widgets) ---

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        """Return preferred (width, height) for this widget.

        The GUIManager / layout will call this during the measure pass.
        Concrete widgets should use gui.measure_text(...) etc.
        """
        return self.width or 0, self.height or 0

    # --- Layout results ---

    def set_rect(self, x: float, y: float, width: float, height: float) -> None:
        """Called by layout manager after computing position and size."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def get_rect(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.width, self.height

    # --- Drawing ---

    def draw(self, gui: "GUIManager") -> None:
        """Draw this widget and its children using the provided GUIManager.

        GUIManager provides access to the Renderer and helpers.
        Subclasses should call super().draw(gui) after drawing themselves
        if they want children drawn (or manage clipping themselves).
        """
        if not self._visible:
            return
        for child in self.children:
            child.draw(gui)

    # --- Input ---

    def contains(self, x: float, y: float) -> bool:
        """Hit test in virtual coordinates."""
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def on_mouse_enter(self, *, gui: Optional["GUIManager"] = None) -> None:
        self._hovered = True

    def on_mouse_leave(self, *, gui: Optional["GUIManager"] = None) -> None:
        self._hovered = False
        self._pressed = False

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        """Return True if the event was consumed."""
        if self.contains(x, y) and not self._disabled:
            self._pressed = True
            return True
        return False

    def on_mouse_release(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self._pressed and self.contains(x, y) and not self._disabled:
            self._pressed = False
            self.on_click()
            return True
        self._pressed = False
        return False

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        """Called while mouse button is held and moving. For text selection etc."""
        pass

    def on_mouse_motion(
        self, x: float, y: float, *, gui: Optional["GUIManager"] = None
    ) -> None:
        """Called every frame with current mouse position for hover effects (e.g. menu highlights)."""
        pass

    def on_click(self) -> None:
        """Override in Button etc."""
        pass

    def on_key(self, key: int, text: str, mod: int = 0) -> bool:
        """Return True if handled. mod is pygame key mod flags for ctrl/shift etc."""
        return False

    def on_key_state(self, pressed) -> bool:
        """Called every frame with live key state (result of pygame.key.get_pressed()).

        Use for responsive held-key behavior (e.g. repeated backspace while holding).
        Return True if the state was consumed.
        """
        return False

    def can_focus(self) -> bool:
        """Whether this widget can receive keyboard focus."""
        return False

    # --- State ---

    @property
    def hovered(self) -> bool:
        return self._hovered

    @property
    def pressed(self) -> bool:
        return self._pressed

    @property
    def disabled(self) -> bool:
        return self._disabled

    def set_disabled(self, disabled: bool) -> None:
        self._disabled = disabled

    def set_visible(self, visible: bool) -> None:
        self._visible = visible

    # --- Utility for nested / clipping ---

    def clip_rect(self) -> tuple[float, float, float, float]:
        """Return the rect that children should be clipped to (usually self rect)."""
        return self.get_rect()
