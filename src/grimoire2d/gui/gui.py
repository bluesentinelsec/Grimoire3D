"""GUIManager - the main entry point for the in-house GUI system.

It owns a root widget tree, performs layout, dispatches input,
and draws everything using the engine Renderer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import pygame

from ..presentation.renderer import Renderer

if TYPE_CHECKING:
    from .widget import Widget


class GUIManager:
    """Manages a tree of widgets.

    Typical usage in a game loop:

        gui = GUIManager()
        root = Frame(gui)
        # ... add widgets using .grid()
        gui.set_root(root)

        while running:
            vx, vy = win.screen_to_virtual(...)
            gui.handle_mouse(vx, vy, mouse_pressed)
            for event in events:
                gui.handle_event(event)
            gui.handle_key_state()

            gui.layout(virtual_width, virtual_height)
            gui.draw(renderer)
    """

    def __init__(self) -> None:
        self.root: Optional[Widget] = None
        self._focused: Optional[Widget] = None
        self._last_mouse_pos: tuple[float, float] = (0.0, 0.0)
        self._mouse_pressed = False
        self._popups: list[
            Widget
        ] = []  # transient posted popups (menus etc), drawn/hit on top

        # Separate UI scale for consistent appearance across display sizes
        # and when world render_scale changes. UI coordinates are in "UI logical"
        # units; multiply by ui_scale for physical screen pixels.
        self.ui_scale: float = 1.0
        self._renderer: Optional[Renderer] = (
            None  # persisted for measurements during input etc.
        )

    def set_root(self, root: "Widget") -> None:
        self.root = root
        self._focused = None
        self._popups.clear()

    def layout(
        self, width: float, height: float, renderer: Optional[Renderer] = None
    ) -> None:
        """Run layout on the root (and thus the whole tree).

        If renderer is provided, widgets can use accurate text measurement.
        """
        if self.root is None:
            return

        if renderer is not None:
            self._renderer = renderer
        self._current_renderer = renderer  # for measurement
        # Give the root its full available size first
        self.root.set_rect(0, 0, width, height)

        if hasattr(self.root, "layout"):
            # Delegate to container's layout (e.g. Frame with GridLayout)
            self.root.layout(self.root.children, width, height, self)  # type: ignore[attr-defined]

        self._current_renderer = None  # restore after layout if needed
        # Otherwise leaf widgets keep their measured size or explicit size

    def draw(self, renderer: Renderer) -> None:
        """Draw the entire GUI tree + any transient popups (e.g. menus) on top.

        UI logical coordinates are scaled by ui_scale at draw time so that
        the same logical layout produces consistent physical size (and crisp
        appearance) across different display resolutions and world render scales.
        """
        if renderer is not None:
            self._renderer = renderer
        self._current_renderer = renderer
        s = getattr(self, "ui_scale", 1.0) or 1.0
        if self.root is not None:
            if abs(s - 1.0) > 1e-6:
                self._scale_tree(self.root, s)
            self.root.draw(self)  # type: ignore[arg-type]
            if abs(s - 1.0) > 1e-6:
                self._scale_tree(self.root, 1.0 / s)
        # Draw popups last so they appear above all normal content
        for popup in self._popups:
            if getattr(popup, "_visible", True):
                if abs(s - 1.0) > 1e-6:
                    self._scale_tree(popup, s)
                popup.draw(self)  # type: ignore[arg-type]
                if abs(s - 1.0) > 1e-6:
                    self._scale_tree(popup, 1.0 / s)
        self._current_renderer = None

    def _scale_tree(self, widget: "Widget", factor: float) -> None:
        """Temporarily scale widget geometry for draw-time UI scaling."""
        widget.x *= factor
        widget.y *= factor
        widget.width *= factor
        widget.height *= factor
        for child in getattr(widget, "children", []):
            self._scale_tree(child, factor)

    _current_renderer: Optional[Renderer] = None

    # ------------------------------------------------------------------
    # Input dispatch (called from the main game loop)
    # ------------------------------------------------------------------

    def handle_mouse(self, x: float, y: float, pressed: bool) -> None:
        """Update hover / press state. Call every frame with *physical* mouse.

        Mouse coords are converted using ui_scale to the GUI's logical space.
        """
        if self.ui_scale != 1.0 and self.ui_scale > 0:
            x = x / self.ui_scale
            y = y / self.ui_scale
        self._last_mouse_pos = (x, y)

        if self.root is None and not self._popups:
            return

        # Popups (menus etc.) take priority for hit testing (they float above)
        widget = self._hit_popup(x, y)
        if widget is None:
            if self.root is not None:
                widget = self._hit_test(self.root, x, y)

        # Hover tracking
        if widget is not self._hovered_widget:
            if hasattr(self, "_hovered_widget") and self._hovered_widget:
                self._hovered_widget.on_mouse_leave(gui=self)
            self._hovered_widget = widget
            if widget:
                widget.on_mouse_enter(gui=self)

        # Motion for hover effects (menu row highlights etc.)
        if self._hovered_widget:
            self._hovered_widget.on_mouse_motion(x, y, gui=self)

        # Outside-click dismiss for active popups (standard menu behavior)
        if pressed and not self._mouse_pressed:
            any_posted = bool(self._popups) or self._any_posted_menu()
            if any_posted:
                hit_popup = self._hit_popup(x, y)
                if hit_popup is None and not self._hit_posted_menu_at_point(x, y):
                    self.dismiss_popups()
                    self._dismiss_tree_posted_menus()

        # Press / release
        if pressed and not self._mouse_pressed:
            if widget:
                widget.on_mouse_press(x, y, 1, gui=self)
                if widget is not self._focused:
                    self._set_focus(widget)
            self._mouse_pressed = True
        elif pressed and self._mouse_pressed:
            # drag while pressed (for text selection etc)
            if self._focused:
                self._focused.on_mouse_drag(x, y, 1, gui=self)
        elif not pressed and self._mouse_pressed:
            if widget:
                widget.on_mouse_release(x, y, 1, gui=self)
            self._mouse_pressed = False

    _hovered_widget: Optional[Widget] = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard etc. Return True if the event was consumed by the GUI."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                shift = bool(event.mod & pygame.KMOD_SHIFT)
                self._move_focus(backward=shift)
                return True  # swallow tab for focus change
            # Give top popup (menu) first chance at keys (Esc closes, arrows navigate)
            if self._popups:
                top = self._popups[-1]
                if hasattr(top, "on_key"):
                    if top.on_key(
                        event.key,
                        event.unicode if hasattr(event, "unicode") else "",
                        getattr(event, "mod", 0),
                    ):
                        return True
            if self._focused is not None:
                consumed = self._focused.on_key(
                    event.key,
                    event.unicode if hasattr(event, "unicode") else "",
                    getattr(event, "mod", 0),
                )
                return consumed
        return False

    def handle_key_state(self) -> bool:
        """Poll live keyboard state for held-key responsive input.

        Call every frame (after handle_event/handle_mouse is fine).
        Focused widget (and top popup) receive on_key_state(pressed_array).
        """
        if self.root is None and not self._popups:
            return False
        pressed = pygame.key.get_pressed()
        # Popups (menus etc.) get first chance at held state too
        if self._popups:
            top = self._popups[-1]
            if hasattr(top, "on_key_state"):
                if top.on_key_state(pressed):
                    return True
        if self._focused is not None:
            if hasattr(self._focused, "on_key_state"):
                return bool(self._focused.on_key_state(pressed))
        return False

    def _hit_test(self, widget: "Widget", x: float, y: float) -> Optional["Widget"]:
        """Depth-first hit test. Returns the topmost (last drawn) widget under the point."""
        if not widget._visible or not widget.contains(x, y):
            return None

        # Check children first (they are drawn on top)
        for child in reversed(widget.children):
            hit = self._hit_test(child, x, y)
            if hit is not None:
                return hit

        return widget

    def _set_focus(self, widget: Optional["Widget"]) -> None:
        if self._focused is not None and self._focused is not widget:
            self._focused._focused = False
        self._focused = widget
        if widget is not None:
            widget._focused = True

    def _get_focusable_widgets(self) -> list["Widget"]:
        """Depth-first collection of focusable widgets."""
        focusables: list["Widget"] = []

        def traverse(w: "Widget"):
            if w.can_focus():
                focusables.append(w)
            for child in w.children:
                traverse(child)

        if self.root:
            traverse(self.root)
        return focusables

    def _move_focus(self, backward: bool = False) -> None:
        focusables = self._get_focusable_widgets()
        if not focusables:
            return
        try:
            current_idx = focusables.index(self._focused) if self._focused else -1
        except ValueError:
            current_idx = -1
        if backward:
            new_idx = (current_idx - 1) % len(focusables)
        else:
            new_idx = (current_idx + 1) % len(focusables)
        self._set_focus(focusables[new_idx])

    # ------------------------------------------------------------------
    # Helpers exposed to widgets
    # ------------------------------------------------------------------

    def measure_text(self, text: str, font_size: int = 16) -> tuple[float, float]:
        """Widgets call this during measure() to get text size.

        Delegates to Renderer if one is available (during layout or draw).
        Falls back to approximation otherwise.
        """
        r = self.get_renderer()
        if r is not None:
            try:
                return r.measure_text(text, font_size=font_size)
            except Exception:
                pass
        # Fallback approximation
        return len(text) * (font_size * 0.55), font_size * 1.3

    def get_renderer(self) -> Optional[Renderer]:
        return getattr(self, "_current_renderer", None) or getattr(
            self, "_renderer", None
        )

    # ------------------------------------------------------------------
    # Popup / transient menu support (used by Menu / Menubutton)
    # ------------------------------------------------------------------

    def _hit_popup(self, x: float, y: float) -> Optional["Widget"]:
        """Return the topmost popup under (x,y) if any."""
        for popup in reversed(self._popups):
            if getattr(popup, "_visible", True) and popup.contains(x, y):
                return popup
        return None

    def post_popup(self, popup: "Widget", x: float, y: float) -> None:
        """Position and register a transient popup (e.g. Menu) so it draws and receives input on top."""
        # Let the popup set its own size/rect via its post() if it has one; otherwise set directly
        if hasattr(popup, "post"):
            try:
                popup.post(x, y)  # type: ignore[attr-defined]
            except Exception:
                popup.x = x
                popup.y = y
        else:
            popup.x = x
            popup.y = y
        if getattr(popup, "_visible", None) is not None:
            popup._visible = True  # type: ignore[attr-defined]
        if popup not in self._popups:
            self._popups.append(popup)
        # Also ensure it is at the end of its parent's children list so normal tree walk prefers it
        parent = getattr(popup, "parent", None)
        if parent is not None and hasattr(parent, "children"):
            if popup in parent.children:
                parent.children.remove(popup)
            parent.children.append(popup)

    def dismiss_popups(self) -> None:
        """Unpost / hide all current popups."""
        for popup in list(self._popups):
            if hasattr(popup, "unpost"):
                try:
                    popup.unpost()  # type: ignore[attr-defined]
                except Exception:
                    pass
            else:
                setattr(popup, "_visible", False)
                setattr(popup, "_posted", False)
        self._popups.clear()

    def _any_posted_menu(self) -> bool:
        if not self.root:
            return False

        def walk(w):
            if getattr(w, "_posted", False) and hasattr(w, "unpost"):
                return True
            for c in getattr(w, "children", []):
                if walk(c):
                    return True
            return False

        return walk(self.root)

    def _dismiss_tree_posted_menus(self) -> None:
        if not self.root:
            return

        def walk(w):
            if getattr(w, "_posted", False) and hasattr(w, "unpost"):
                try:
                    w.unpost()
                except Exception:
                    pass
            for c in getattr(w, "children", []):
                walk(c)

        walk(self.root)

    def _hit_posted_menu_at_point(self, x: float, y: float) -> bool:
        if not self.root:
            return False

        def walk(w):
            if (
                getattr(w, "_posted", False)
                and hasattr(w, "contains")
                and w.contains(x, y)
            ):
                return True
            for c in getattr(w, "children", []):
                if walk(c):
                    return True
            return False

        return walk(self.root)
