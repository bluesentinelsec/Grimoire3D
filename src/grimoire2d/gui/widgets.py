"""Basic concrete widgets for the in-house GUI.

Currently includes:
- Frame (container with grid)
- Label
- Button
- Checkbutton
- Radiobutton
- Entry
- Text (multi-line)
- Listbox
- Combobox
- Spinbox
- Scale
- Scrollbar
- Canvas
- Menu (popup, context, cascades + menubar-style)
- Menubutton
- LabelFrame (framed container with title label)
- PanedWindow (resizable split panes / split views)
- Progressbar (determinate / indeterminate progress indicator)
- Notebook (tabbed notebook interface)
- Treeview (hierarchical tree/list view for hierarchies, browsers)
- Separator (horizontal or vertical line)
- Sizegrip (resize grip / corner handle)

All are designed to work with GridLayout, support nesting inside Frames,
and integrate with the engine's Renderer for drawing and measurement.
"""

# Note: "Checkbox" in older comments refers to Checkbutton.

from __future__ import annotations

import pygame

from typing import TYPE_CHECKING, Any, Callable, Optional

from .layouts import GridLayout
from .widget import Widget

if TYPE_CHECKING:
    from .gui import GUIManager


class Frame(Widget):
    """A container widget that can host children using grid layout."""

    def __init__(self, parent: Optional[Widget] = None) -> None:
        super().__init__(parent)
        self._layout = GridLayout()

    def set_layout(self, layout: GridLayout) -> None:
        self._layout = layout

    def grid_rowconfigure(self, row: int, weight: float = 0, **kwargs: Any) -> None:
        """Tkinter-like: set row weight for expansion in grid."""
        self._layout.set_row_weight(row, weight)

    def grid_columnconfigure(
        self, column: int, weight: float = 0, **kwargs: Any
    ) -> None:
        """Tkinter-like: set column weight for expansion in grid."""
        self._layout.set_column_weight(column, weight)

    def layout(
        self,
        children: list[Widget],
        avail_w: float,
        avail_h: float,
        gui: Optional["GUIManager"] = None,
    ) -> None:
        """Run the grid layout on our children."""
        # Re-register children that have grid options
        self._layout.cells.clear()
        for child in children:
            if child.grid_options is not None:
                self._layout.add(child, child.grid_options)

        self._layout.layout(children, avail_w, avail_h, gui)

        # After grid layout (which sets local coords for direct children),
        # translate direct children rects to be absolute (add this Frame\'s position)
        fx, fy = self.x, self.y
        for child in children:
            if child.grid_options is not None:
                cx, cy, cw, ch = child.get_rect()
                child.set_rect(fx + cx, fy + cy, cw, ch)

        # Recurse into nested containers
        for child in children:
            if hasattr(child, "layout") and child.grid_options is not None:
                child_w = child.width
                child_h = child.height
                child.layout(child.children, child_w, child_h, gui)

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        """Preferred size based on content grid."""
        if not self.children:
            return 100.0, 30.0  # default empty frame
        return self._layout.get_preferred_size(self.children, gui)

    def draw(self, gui: "GUIManager") -> None:
        # Simple frame background (can be extended with borders, themes later)
        if gui.get_renderer():
            r = gui.get_renderer()
            # Only draw bg if we have explicit size or children
            if self.width > 0 and self.height > 0:
                r.draw_rect(
                    self.x, self.y, self.width, self.height, (0.18, 0.18, 0.2, 0.85)
                )
                r.draw_rect_border(
                    self.x, self.y, self.width, self.height, 1.0, (0.3, 0.3, 0.35, 1.0)
                )

        super().draw(gui)


class Label(Widget):
    """Simple text label."""

    def __init__(
        self, parent: Optional[Widget] = None, text: str = "", font_size: int = 16
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.font_size = font_size

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui is not None:
            w, h = gui.measure_text(self.text, self.font_size)
        else:
            w, h = len(self.text) * (self.font_size * 0.55), self.font_size * 1.3
        return w, h

    def draw(self, gui: "GUIManager") -> None:
        if gui.get_renderer():
            gui.get_renderer().draw_text(
                self.text,
                self.x,
                self.y,
                color=(0.9, 0.9, 0.9, 1.0),
                font_size=self.font_size,
            )
        # Labels usually don't have children


class Button(Widget):
    """Clickable button with text."""

    def __init__(
        self,
        parent: Optional[Widget] = None,
        text: str = "",
        command: Optional[Callable[[], None]] = None,
        font_size: int = 16,
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.command = command
        self.font_size = font_size
        self._min_width = 80
        self._min_height = 26

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui is not None:
            w, h = gui.measure_text(self.text, self.font_size)
        else:
            w, h = len(self.text) * (self.font_size * 0.55), self.font_size * 1.3
        return max(w + 20, self._min_width), max(h + 8, self._min_height)

    def on_click(self) -> None:
        if self.command:
            self.command()

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        # Simple button styling based on state
        if self.disabled:
            bg = (0.25, 0.25, 0.25, 1.0)
            border = (0.35, 0.35, 0.35, 1.0)
            text_c = (0.5, 0.5, 0.5, 1.0)
        elif self.pressed:
            bg = (0.15, 0.15, 0.18, 1.0)
            border = (0.1, 0.4, 0.8, 1.0)
            text_c = (1.0, 1.0, 1.0, 1.0)
        elif self.hovered:
            bg = (0.35, 0.35, 0.38, 1.0)
            border = (0.2, 0.5, 0.9, 1.0)
            text_c = (1.0, 1.0, 1.0, 1.0)
        else:
            bg = (0.28, 0.28, 0.30, 1.0)
            border = (0.15, 0.15, 0.18, 1.0)
            text_c = (0.95, 0.95, 0.95, 1.0)

        r.draw_rect(self.x, self.y, self.width, self.height, bg)
        r.draw_rect_border(self.x, self.y, self.width, self.height, 1.5, border)

        tw, th = gui.measure_text(self.text, self.font_size)
        tx = self.x + (self.width - tw) / 2
        ty = self.y + (self.height - th) / 2
        r.draw_text(self.text, tx, ty, color=text_c, font_size=self.font_size)


class Checkbutton(Widget):
    """Checkbox with label, Tkinter-like."""

    def __init__(
        self,
        parent: Optional[Widget] = None,
        text: str = "",
        variable: Optional[list] = None,  # simple mutable bool holder [bool]
        command: Optional[Callable[[], None]] = None,
        font_size: int = 16,
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.variable = variable or [False]
        self.command = command
        self.font_size = font_size
        self._box_size = 14

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui is not None:
            tw, th = gui.measure_text(self.text, self.font_size)
        else:
            tw, th = len(self.text) * (self.font_size * 0.55), self.font_size * 1.3
        return self._box_size + 6 + tw, max(self._box_size, th)

    def on_click(self) -> None:
        self.variable[0] = not self.variable[0]
        if self.command:
            self.command()

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        # Checkbox box
        bx = self.x
        by = self.y + (self.height - self._box_size) / 2
        r.draw_rect(bx, by, self._box_size, self._box_size, (0.15, 0.15, 0.17, 1.0))
        r.draw_rect_border(
            bx, by, self._box_size, self._box_size, 1.0, (0.4, 0.4, 0.45, 1.0)
        )

        if self.variable[0]:
            # simple check mark
            r.draw_line(bx + 3, by + 7, bx + 6, by + 11, 1.5, (0.3, 0.8, 0.3, 1.0))
            r.draw_line(bx + 6, by + 11, bx + 12, by + 3, 1.5, (0.3, 0.8, 0.3, 1.0))

        # Label
        if gui.get_renderer():
            tw, th = gui.measure_text(self.text, self.font_size)
            tx = bx + self._box_size + 6
            ty = self.y + (self.height - th) / 2
            r.draw_text(
                self.text, tx, ty, color=(0.9, 0.9, 0.9, 1.0), font_size=self.font_size
            )


class Radiobutton(Widget):
    """Radio button with label. Mutually exclusive selection via shared variable.

    Tkinter-like:
        selected = [0]
        r1 = Radiobutton(root, text="Option A", variable=selected, value=0)
        r1.grid(...)
        r2 = Radiobutton(root, text="Option B", variable=selected, value=1)
        r2.grid(...)
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        text: str = "",
        variable: Optional[list] = None,  # shared holder [current_value]
        value: Any = 0,
        command: Optional[Callable[[], None]] = None,
        font_size: int = 16,
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.variable = variable or [0]
        self.value = value
        self.command = command
        self.font_size = font_size
        self._circle_size = 14
        self._dot_size = 6

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui is not None:
            tw, th = gui.measure_text(self.text, self.font_size)
        else:
            tw, th = len(self.text) * (self.font_size * 0.55), self.font_size * 1.3
        return self._circle_size + 6 + tw, max(self._circle_size, th)

    def on_click(self) -> None:
        if self.variable[0] != self.value:
            self.variable[0] = self.value
            if self.command:
                self.command()

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        # Radio circle position
        bx = self.x
        by = self.y + (self.height - self._circle_size) / 2
        cx = bx + self._circle_size / 2
        cy = by + self._circle_size / 2

        # Filled circle bg
        r.draw_circle(cx, cy, self._circle_size / 2 - 0.5, (0.15, 0.15, 0.17, 1.0))
        # Border ring approx via border on rect (or could skip for simplicity)
        r.draw_rect_border(
            bx, by, self._circle_size, self._circle_size, 1.0, (0.4, 0.4, 0.45, 1.0)
        )

        if self.variable and self.variable[0] == self.value:
            # inner dot
            r.draw_circle(cx, cy, self._dot_size / 2, (0.3, 0.8, 0.3, 1.0))

        # Label
        if gui.get_renderer():
            tw, th = gui.measure_text(self.text, self.font_size)
            tx = bx + self._circle_size + 6
            ty = self.y + (self.height - th) / 2
            r.draw_text(
                self.text, tx, ty, color=(0.9, 0.9, 0.9, 1.0), font_size=self.font_size
            )


class Entry(Widget):
    """Single-line text entry field, Tkinter-like.

    Supports:
    - Typing, backspace, delete, arrows, home/end
    - Click to place cursor / drag to highlight text
    - Text selection highlighting
    - Focus swallowing of keyboard input
    - Ctrl+A (select all), Ctrl+C (copy), Ctrl+V (paste), Ctrl+X (cut)
    - Shift+arrows for extending selection
    - Tab / Shift+Tab moves focus to next/prev focusable widget (via GUIManager)
    - .get() / .set_text() / .insert() / .delete()
    - grid() placement and nesting inside Frames
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        text: str = "",
        width: int = 20,
        font_size: int = 16,
        show: Optional[str] = None,  # e.g. '*' for password
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._width_chars = width
        self.font_size = font_size
        self.show = show
        self._cursor_pos = len(text)
        self._anchor: Optional[int] = None
        self._selection: Optional[tuple[int, int]] = None
        self._min_height = 24
        self._scroll_offset: float = 0.0
        # For responsive held-key repeat (backspace, arrows etc) via key state polling
        self._next_repeat: dict[int, int] = {}
        self._repeat_delay = 300
        self._repeat_interval = 50

    @property
    def text(self) -> str:
        return self._text

    def get(self) -> str:
        return self._text

    def set_text(self, value: str) -> None:
        self._text = value
        self._cursor_pos = len(value)
        self._anchor = None
        self._selection = None
        self._scroll_offset = 0.0

    def insert(self, index: int, text: str) -> None:
        if index < 0:
            index = 0
        if index > len(self._text):
            index = len(self._text)
        self._text = self._text[:index] + text + self._text[index:]
        self._cursor_pos = index + len(text)
        self._adjust_scroll()

    def delete(self, start: int, end: Optional[int] = None) -> None:
        if end is None:
            end = start + 1
        self._text = self._text[:start] + self._text[end:]
        self._cursor_pos = min(start, len(self._text))
        self._adjust_scroll()

    def _display_text(self) -> str:
        if self.show:
            return self.show * len(self._text)
        return self._text

    def _text_width(self, text: str, gui: Optional["GUIManager"] = None) -> float:
        if not text:
            return 0.0
        if gui is not None:
            w, _ = gui.measure_text(text, self.font_size)
            return w
        return len(text) * (self.font_size * 0.55)

    def can_focus(self) -> bool:
        return not self._disabled

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui is not None:
            sample = "W" * max(self._width_chars, 1)
            w, h = gui.measure_text(sample, self.font_size)
        else:
            w = self._width_chars * (self.font_size * 0.55)
            h = self.font_size * 1.3
        return w + 8, max(h + 6, self._min_height)

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self.contains(x, y) and not self._disabled:
            self._pressed = True
            self._cursor_pos = self._char_index_at_x(x, gui)
            self._anchor = self._cursor_pos
            self._selection = None
            self._adjust_scroll(gui)
            return True
        return False

    def on_click(self) -> None:
        # Selection/cursor already set during press and drag.
        # on release we just keep the selection or cursor.
        pass

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        if self._disabled:
            return
        self._cursor_pos = self._char_index_at_x(x, gui)
        if self._anchor is None:
            self._anchor = self._cursor_pos
        self._update_selection()
        self._adjust_scroll(gui)

    def _char_index_at_x(
        self, mouse_x: float, gui: Optional["GUIManager"] = None
    ) -> int:
        disp = self._display_text()
        if not disp:
            return 0
        text_x = self.x + 4
        rel_x = mouse_x - text_x + self._scroll_offset
        if rel_x <= 0:
            return 0
        n = len(disp)
        # Compute insertion index by finding the character boundary whose
        # measured position is closest to the click. This ensures clicks land
        # on the visually correct character even with proportional fonts and
        # accurate renderer.measure_text (used in drawing).
        best_idx = 0
        min_diff = abs(rel_x)  # distance to 0
        for i in range(1, n + 1):
            prefix = disp[:i]
            if gui is not None:
                try:
                    w, _ = gui.measure_text(prefix, self.font_size)
                except Exception:
                    w = i * (self.font_size * 0.55)
            else:
                w = i * (self.font_size * 0.55)
            diff = abs(w - rel_x)
            if diff < min_diff:
                min_diff = diff
                best_idx = i
            if w > rel_x:
                # no need to check much further
                break
        return min(n, best_idx)

    def _update_selection(self) -> None:
        if self._anchor is not None and self._anchor != self._cursor_pos:
            s = min(self._anchor, self._cursor_pos)
            e = max(self._anchor, self._cursor_pos)
            self._selection = (s, e)
        else:
            self._selection = None

    def _adjust_scroll(self, gui: Optional["GUIManager"] = None) -> None:
        disp = self._display_text()
        if not disp:
            self._scroll_offset = 0.0
            return
        prefix = disp[: self._cursor_pos]
        cur_x = self._text_width(prefix, gui)
        visible_w = max(1.0, self.width - 8) if self.width > 0 else 200.0
        if cur_x < self._scroll_offset:
            self._scroll_offset = max(0.0, cur_x - visible_w * 0.25)
        elif cur_x > self._scroll_offset + visible_w:
            self._scroll_offset = cur_x - visible_w * 0.75
        full_w = self._text_width(disp, gui)
        self._scroll_offset = max(
            0.0, min(self._scroll_offset, max(0.0, full_w - visible_w))
        )

    def _handle_held_edit_key(self, key: int, mod: int) -> bool:
        """Core implementation for navigation/delete actions.

        Used by both on_key (discrete) and on_key_state (held/polled).
        Returns True if action taken.
        """
        shift = bool(mod & pygame.KMOD_SHIFT)

        if key == pygame.K_LEFT:
            if shift:
                if self._anchor is None:
                    self._anchor = self._cursor_pos
                self._cursor_pos = max(0, self._cursor_pos - 1)
                self._update_selection()
            else:
                if self._selection:
                    self._cursor_pos = min(self._selection)
                    self._anchor = None
                    self._selection = None
                else:
                    self._cursor_pos = max(0, self._cursor_pos - 1)
            self._adjust_scroll()
            return True

        if key == pygame.K_RIGHT:
            if shift:
                if self._anchor is None:
                    self._anchor = self._cursor_pos
                self._cursor_pos = min(len(self._text), self._cursor_pos + 1)
                self._update_selection()
            else:
                if self._selection:
                    self._cursor_pos = max(self._selection)
                    self._anchor = None
                    self._selection = None
                else:
                    self._cursor_pos = min(len(self._text), self._cursor_pos + 1)
            self._adjust_scroll()
            return True

        if key == pygame.K_HOME:
            if shift:
                if self._anchor is None:
                    self._anchor = self._cursor_pos
                self._cursor_pos = 0
                self._update_selection()
            else:
                if self._selection:
                    self._cursor_pos = 0
                    self._anchor = None
                    self._selection = None
                else:
                    self._cursor_pos = 0
            self._adjust_scroll()
            return True

        if key == pygame.K_END:
            if shift:
                if self._anchor is None:
                    self._anchor = self._cursor_pos
                self._cursor_pos = len(self._text)
                self._update_selection()
            else:
                if self._selection:
                    self._cursor_pos = len(self._text)
                    self._anchor = None
                    self._selection = None
                else:
                    self._cursor_pos = len(self._text)
            self._adjust_scroll()
            return True

        if key == pygame.K_BACKSPACE:
            if self._selection:
                s, e = sorted(self._selection)
                self._text = self._text[:s] + self._text[e:]
                self._cursor_pos = s
                self._anchor = None
                self._selection = None
            elif self._cursor_pos > 0:
                self.delete(self._cursor_pos - 1)
            self._adjust_scroll()
            return True

        if key == pygame.K_DELETE:
            if self._selection:
                s, e = sorted(self._selection)
                self._text = self._text[:s] + self._text[e:]
                self._cursor_pos = s
                self._anchor = None
                self._selection = None
            elif self._cursor_pos < len(self._text):
                self.delete(self._cursor_pos)
            self._adjust_scroll()
            return True

        return False

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        if self._disabled:
            return False

        ctrl = bool(mod & (pygame.KMOD_CTRL | pygame.KMOD_META))

        # Ctrl hotkeys
        if ctrl:
            if key == pygame.K_a:  # select all
                self._anchor = 0
                self._cursor_pos = len(self._text)
                self._update_selection()
                self._adjust_scroll()
                return True
            if key == pygame.K_c:  # copy
                if self._selection:
                    s, e = self._selection
                    clip = self._text[s:e]
                    try:
                        pygame.scrap.init()
                        pygame.scrap.put(pygame.SCRAP_TEXT, clip.encode("utf-8"))
                    except Exception:
                        pass
                return True
            if key == pygame.K_v:  # paste
                try:
                    pygame.scrap.init()
                    data = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if data:
                        paste = data.decode("utf-8", errors="ignore").replace("\0", "")
                        if self._selection:
                            s, e = sorted(self._selection)
                            self._text = self._text[:s] + paste + self._text[e:]
                            self._cursor_pos = s + len(paste)
                            self._anchor = None
                            self._selection = None
                        else:
                            self.insert(self._cursor_pos, paste)
                            self._cursor_pos += len(paste)
                        self._adjust_scroll()
                except Exception:
                    pass
                return True
            if key == pygame.K_x:  # cut
                if self._selection:
                    s, e = sorted(self._selection)
                    clip = self._text[s:e]
                    try:
                        pygame.scrap.init()
                        pygame.scrap.put(pygame.SCRAP_TEXT, clip.encode("utf-8"))
                    except Exception:
                        pass
                    self._text = self._text[:s] + self._text[e:]
                    self._cursor_pos = s
                    self._anchor = None
                    self._selection = None
                    self._adjust_scroll()
                return True
            # ignore other ctrl for now
            return False

        repeatables = (
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_HOME,
            pygame.K_END,
            pygame.K_BACKSPACE,
            pygame.K_DELETE,
        )

        if key in repeatables:
            handled = self._handle_held_edit_key(key, mod)
            if handled:
                now = pygame.time.get_ticks()
                # Schedule next: use shorter interval if this was a scheduled repeat fire
                scheduled = self._next_repeat.get(key, 0)
                use_delay = not scheduled or now < scheduled - 5
                wait = self._repeat_delay if use_delay else self._repeat_interval
                self._next_repeat[key] = now + wait
                return True

        if key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_TAB):
            # consume but don't insert; tab is handled at GUI level
            return True

        if char and ord(char) >= 32:
            if self._selection:
                s, e = sorted(self._selection)
                self._text = self._text[:s] + char + self._text[e:]
                self._cursor_pos = s + len(char)
                self._anchor = None
                self._selection = None
            else:
                self.insert(self._cursor_pos, char)
            self._adjust_scroll()
            return True

        return False

    def on_key_state(self, pressed) -> bool:
        """Responsive held key handling via direct state (buffered input)."""
        if self._disabled or not self._focused:
            return False
        now = pygame.time.get_ticks()
        mod = pygame.key.get_mods()

        repeatables = (
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_HOME,
            pygame.K_END,
            pygame.K_BACKSPACE,
            pygame.K_DELETE,
        )

        # Clear released keys so future presses get fresh delay
        for k in list(self._next_repeat.keys()):
            if not pressed[k]:
                self._next_repeat.pop(k, None)

        acted = False
        for k in repeatables:
            if not pressed[k]:
                continue
            nxt = self._next_repeat.get(k, 0)
            if nxt == 0:
                # First time we see it held through state (or after release)
                self._next_repeat[k] = now + self._repeat_delay
                if self._handle_held_edit_key(k, mod):
                    acted = True
                continue
            if now >= nxt:
                if self._handle_held_edit_key(k, mod):
                    self._next_repeat[k] = now + self._repeat_interval
                    acted = True
        return acted

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        # Background
        bg = (0.12, 0.12, 0.13, 1.0) if not self._disabled else (0.15, 0.15, 0.15, 1.0)
        r.draw_rect(self.x, self.y, self.width, self.height, bg)
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.25, 0.25, 0.28, 1.0)
        )

        # Text + horizontal scrolling + clipping to prevent overflow
        disp = self._display_text()
        text_x = self.x + 4
        text_y = self.y + 3

        self._adjust_scroll(gui)
        visible_w = max(1.0, self.width - 8)

        # Clip to entry interior so long text doesn't spill
        clip_x = self.x + 2
        clip_y = self.y + 1
        clip_w = self.width - 4
        clip_h = self.height - 2
        r.push_clip(clip_x, clip_y, clip_w, clip_h)

        # Selection highlight (offset by scroll)
        if self._selection:
            s, e = self._selection
            pre_w = self._text_width(disp[:s], gui) - self._scroll_offset
            sel_w = self._text_width(disp[s:e], gui)
            r.draw_rect(
                text_x + pre_w,
                text_y,
                max(1.0, sel_w),
                self.height - 6,
                (0.25, 0.45, 0.75, 0.6),
            )

        # Draw (possibly scrolled) text
        r.draw_text(
            disp,
            text_x - self._scroll_offset,
            text_y,
            color=(0.9, 0.9, 0.9, 1.0),
            font_size=self.font_size,
        )

        # Cursor when focused
        if self._focused and not self._disabled:
            prefix = disp[: self._cursor_pos]
            cx = self._text_width(prefix, gui) - self._scroll_offset
            cursor_x = text_x + cx
            cursor_h = self.height - 6
            if 0 <= cx <= visible_w + 2:  # visible within clip
                r.draw_rect(cursor_x, text_y, 1.5, cursor_h, (0.8, 0.8, 0.85, 1.0))

        r.pop_clip()


class Text(Widget):
    """Multi-line text editor widget, Tkinter Text-like.

    Supports:
    - Multi-line editing with Enter for new lines.
    - Cursor movement (arrows, home, end, up/down between lines).
    - Selection with mouse drag and Shift+arrows (multi-line).
    - Copy, paste, cut, select-all with Ctrl hotkeys.
    - Marks: 'insert', 'sel.first', 'sel.last' (and user marks).
    - Tags: tag_add, tag_config (e.g. foreground, background), applied on draw.
    - .insert(index, text), .delete(start, end), .get(start, end)
    - mark_set(name, index), tag_add(tag, start, end)
    - Grid layout and nesting support.
    - Swallows input when focused; Tab can be handled by GUI for focus or inserted.
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        width: int = 40,  # in chars
        height: int = 10,  # in lines (for initial measure)
        font_size: int = 14,
    ) -> None:
        super().__init__(parent)
        self._lines: list[str] = [""]
        self._marks: dict[str, tuple[int, int]] = {"insert": (0, 0)}
        self._tags: dict[
            str, dict
        ] = {}  # tag -> {"ranges": [(start, end), ...], "config": {...}}
        self._sel_start: Optional[tuple[int, int]] = None
        self._sel_end: Optional[tuple[int, int]] = None
        self._width_chars = width
        self._height_lines = height
        self.font_size = font_size
        self._min_height = 20
        # for mouse selection
        self._drag_anchor: Optional[tuple[int, int]] = None
        # scrolling support for Scrollbar
        self._y_scroll = 0
        self.yscrollcommand = None
        # held key repeat state (for responsive backspace/arrows while held)
        self._next_repeat: dict[int, int] = {}
        self._repeat_delay = 300
        self._repeat_interval = 50

    def _schedule_text_repeat(self, key: int, use_delay: bool = True) -> None:
        now = pygame.time.get_ticks()
        wait = self._repeat_delay if use_delay else self._repeat_interval
        self._next_repeat[key] = now + wait

    def yview(self, *args):
        if args:
            if args[0] == "moveto":
                self.yview_moveto(args[1])
            elif args[0] == "scroll":
                self.yview_scroll(*args[1:])
            return
        total = max(1, len(self._lines))
        visible = max(
            1, int(self.height / (self.font_size * 1.3)) if self.height else 5
        )
        first = self._y_scroll / total
        last = min(1.0, (self._y_scroll + visible) / total)
        if self.yscrollcommand:
            try:
                self.yscrollcommand(first, last)
            except Exception:
                pass
        return first, last

    def yview_moveto(self, fraction):
        total = max(1, len(self._lines))
        self._y_scroll = max(0, min(int(fraction * total), total - 1))
        self.yview()  # trigger command

    def yview_scroll(self, number, what="units"):
        if what == "units":
            delta = int(number)
        else:
            visible = max(
                1, int(self.height / (self.font_size * 1.3)) if self.height else 5
            )
            delta = int(number) * visible
        self._y_scroll = max(0, min(self._y_scroll + delta, len(self._lines) - 1))
        self.yview()

    # --- Index / mark / tag helpers ---

    def _parse_index(self, index: Any) -> tuple[int, int]:
        if isinstance(index, (list, tuple)) and len(index) == 2:
            line, col = int(index[0]), int(index[1])
            return (max(0, line), max(0, col))
        if isinstance(index, str):
            if index == "end":
                line_idx = len(self._lines) - 1
                return (line_idx, len(self._lines[line_idx]))
            if index == "insert":
                return self._marks.get("insert", (0, 0))
            if index == "sel.first":
                if self._sel_start and self._sel_end:
                    return min(self._sel_start, self._sel_end)
                return self._marks.get("insert", (0, 0))
            if index == "sel.last":
                if self._sel_start and self._sel_end:
                    return max(self._sel_start, self._sel_end)
                return self._marks.get("insert", (0, 0))
            if "." in index:
                try:
                    line_idx, col = index.split(".")
                    return (int(line_idx) - 1 if int(line_idx) > 0 else 0, int(col))
                except Exception:
                    pass
        return (0, 0)

    def _format_index(self, pos: tuple[int, int]) -> str:
        return f"{pos[0] + 1}.{pos[1]}"

    def _clamp_pos(self, pos: tuple[int, int]) -> tuple[int, int]:
        line = max(0, min(pos[0], len(self._lines) - 1))
        col = max(0, min(pos[1], len(self._lines[line])))
        return (line, col)

    def mark_set(self, name: str, index: Any) -> None:
        pos = self._clamp_pos(self._parse_index(index))
        self._marks[name] = pos
        if name == "insert":
            # keep in sync with cursor if using
            pass

    def mark_unset(self, name: str) -> None:
        if name in self._marks and name not in ("insert",):  # keep insert
            del self._marks[name]

    def tag_add(self, tagName: str, start: Any, end: Any) -> None:
        s = self._parse_index(start)
        e = self._parse_index(end)
        if tagName not in self._tags:
            self._tags[tagName] = {"ranges": [], "config": {}}
        self._tags[tagName]["ranges"].append((s, e))

    def tag_remove(self, tagName: str, start: Any, end: Any) -> None:
        if tagName not in self._tags:
            return
        s = self._parse_index(start)
        e = self._parse_index(end)
        new_ranges = []
        for rs, re in self._tags[tagName]["ranges"]:
            # simple: remove exact, for full would intersect, but ok for now
            if rs != s or re != e:
                new_ranges.append((rs, re))
        self._tags[tagName]["ranges"] = new_ranges

    def tag_config(self, tagName: str, **kwargs: Any) -> None:
        if tagName not in self._tags:
            self._tags[tagName] = {"ranges": [], "config": {}}
        self._tags[tagName]["config"].update(kwargs)

    def _get_tag_style(self, pos: tuple[int, int]) -> dict:
        style = {"foreground": (0.9, 0.9, 0.9, 1.0)}
        for tag, info in self._tags.items():
            for rs, re in info.get("ranges", []):
                if self._pos_le(rs, pos) and self._pos_lt(pos, re):
                    cfg = info.get("config", {})
                    if "foreground" in cfg:
                        style["foreground"] = cfg["foreground"]
                    if "background" in cfg:
                        style["background"] = cfg["background"]
                    break
        return style

    def _pos_le(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[0] or (a[0] == b[0] and a[1] <= b[1])

    def _pos_lt(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[0] or (a[0] == b[0] and a[1] < b[1])

    # --- Content ops ---

    def get(self, start: Any = "1.0", end: Any = "end") -> str:
        s = self._parse_index(start)
        e = self._parse_index(end)
        if self._pos_lt(e, s):
            s, e = e, s
        if s[0] == e[0]:
            return self._lines[s[0]][s[1] : e[1]]
        parts = [self._lines[s[0]][s[1] :]]
        for line_idx in range(s[0] + 1, e[0]):
            parts.append(self._lines[line_idx])
        parts.append(self._lines[e[0]][: e[1]])
        return "\n".join(parts)

    def insert(self, index: Any, chars: str) -> None:
        if not chars:
            return
        pos = self._clamp_pos(self._parse_index(index))
        line, col = pos
        # handle \n
        parts = chars.split("\n")
        if len(parts) == 1:
            self._lines[line] = (
                self._lines[line][:col] + parts[0] + self._lines[line][col:]
            )
            new_pos = (line, col + len(parts[0]))
        else:
            left = self._lines[line][:col]
            right = self._lines[line][col:]
            self._lines[line] = left + parts[0]
            new_lines = parts[1:-1]
            last = parts[-1] + right
            insert_idx = line + 1
            for nl in new_lines:
                self._lines.insert(insert_idx, nl)
                insert_idx += 1
            self._lines.insert(insert_idx, last)
            new_pos = (line + len(parts) - 1, len(parts[-1]))
        new_pos = self._clamp_pos(new_pos)
        self.mark_set("insert", new_pos)
        # adjust selection if active
        if self._sel_start and self._sel_end:
            self._adjust_selection_on_edit(pos, len(chars), insert=True)
        self._invalidate_size()

    def delete(self, start: Any, end: Any = None) -> None:
        s = self._clamp_pos(self._parse_index(start))
        if end is None:
            e = (s[0], s[1] + 1)
        else:
            e = self._clamp_pos(self._parse_index(end))
        if self._pos_le(e, s):
            return
        if s[0] == e[0]:
            self._lines[s[0]] = self._lines[s[0]][: s[1]] + self._lines[s[0]][e[1] :]
        else:
            self._lines[s[0]] = self._lines[s[0]][: s[1]] + self._lines[e[0]][e[1] :]
            del self._lines[s[0] + 1 : e[0] + 1]
        self.mark_set("insert", s)
        if self._sel_start and self._sel_end:
            self._adjust_selection_on_edit(s, 0, insert=False)
        self._invalidate_size()

    def _adjust_selection_on_edit(
        self, edit_pos: tuple[int, int], delta: int, insert: bool
    ):
        # naive adjust; real impl more careful with ranges
        if self._sel_start:
            if self._pos_le(edit_pos, self._sel_start):
                if insert:
                    nl, nc = self._sel_start
                    self._sel_start = (nl, nc + delta)
            if self._sel_end and self._pos_le(edit_pos, self._sel_end):
                if insert:
                    nl, nc = self._sel_end
                    self._sel_end = (nl, nc + delta)
        self._update_sel_from_marks()

    # --- Selection and cursor ---

    def _update_sel_from_marks(self):
        sf = self._marks.get("sel.first")
        sl = self._marks.get("sel.last")
        if sf and sl:
            self._sel_start = sf
            self._sel_end = sl
        else:
            self._sel_start = self._sel_end = None

    def _set_selection(self, start: tuple[int, int], end: tuple[int, int]):
        self._sel_start = self._clamp_pos(start)
        self._sel_end = self._clamp_pos(end)
        self.mark_set("sel.first", self._sel_start)
        self.mark_set("sel.last", self._sel_end)

    # --- Measurement and drawing ---

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui is not None:
            max_w = 0
            for line in self._lines:
                w, _ = gui.measure_text(line or " ", self.font_size)
                max_w = max(max_w, w)
            line_h = self.font_size * 1.3
            h = len(self._lines) * line_h
            char_w = (
                max_w
                / max(1, len(self._lines[0]) if self._lines and self._lines[0] else 1)
                if max_w
                else self.font_size * 0.55
            )
            w = self._width_chars * char_w + 8
            return max(w, max_w + 8), max(h + 6, self._min_height)
        else:
            w = self._width_chars * (self.font_size * 0.55) + 8
            h = self._height_lines * (self.font_size * 1.3) + 6
            return w, max(h, self._min_height)

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        # bg
        bg = (0.1, 0.1, 0.11, 1.0) if not self._disabled else (0.12, 0.12, 0.12, 1.0)
        r.draw_rect(self.x, self.y, self.width, self.height, bg)
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.2, 0.2, 0.22, 1.0)
        )

        line_h = self.font_size * 1.3
        pad_x = 4
        text_x = self.x + pad_x
        default_color = (0.9, 0.9, 0.9, 1.0)

        start_line = self._y_scroll
        for i in range(start_line, len(self._lines)):
            y = self.y + (i - start_line) * line_h + 2
            if y > self.y + self.height:
                break
            line = self._lines[i]
            # selection or tag segments
            segments = self._get_line_segments(i, line)

            current_x = text_x
            for seg_text, style in segments:
                if not seg_text:
                    continue
                fg = style.get("foreground", default_color)
                bg = style.get("background")
                if bg:
                    sw, sh = (
                        gui.measure_text(seg_text, self.font_size)
                        if gui
                        else (len(seg_text) * self.font_size * 0.55, line_h)
                    )
                    r.draw_rect(current_x, y, sw, sh, bg)
                r.draw_text(seg_text, current_x, y, color=fg, font_size=self.font_size)
                tw, _ = (
                    gui.measure_text(seg_text, self.font_size)
                    if gui
                    else (len(seg_text) * self.font_size * 0.55, 0)
                )
                current_x += tw

        # cursor
        if self._focused and not self._disabled:
            ins = self._marks.get("insert", (0, 0))
            if start_line <= ins[0] < len(self._lines):
                vis_i = ins[0] - start_line
                y = self.y + vis_i * line_h + 2
                prefix = self._lines[ins[0]][: ins[1]]
                cx, _ = (
                    gui.measure_text(prefix, self.font_size)
                    if gui
                    else (ins[1] * self.font_size * 0.55, 0)
                )
                cursor_x = text_x + cx
                r.draw_rect(cursor_x, y, 1.5, line_h - 2, (0.8, 0.8, 0.85, 1.0))

    def _get_line_segments(self, line_idx: int, line: str) -> list[tuple[str, dict]]:
        """Return [(text, style), ...] for the line, applying tags and selection."""
        # collect tag intervals for this line
        events: dict[int, list] = {}  # col -> list of (type, style)
        for tag, info in self._tags.items():
            for (sl, sc), (el, ec) in info.get("ranges", []):
                if sl <= line_idx <= el:
                    startc = sc if sl == line_idx else 0
                    endc = ec if el == line_idx else len(line)
                    if startc < endc:
                        style = info.get("config", {}).copy()
                        if startc not in events:
                            events[startc] = []
                        events[startc].append(("start", style))
                        if endc not in events:
                            events[endc] = []
                        events[endc].append(("end", style))

        # selection
        if self._sel_start and self._sel_end:
            ss = min(self._sel_start, self._sel_end)
            se = max(self._sel_start, self._sel_end)
            if ss[0] <= line_idx <= se[0]:
                sc = ss[1] if ss[0] == line_idx else 0
                ec = se[1] if se[0] == line_idx else len(line)
                if sc < ec:
                    sel_style = {"background": (0.25, 0.45, 0.75, 0.5)}
                    if sc not in events:
                        events[sc] = []
                    events[sc].append(("start", sel_style))
                    if ec not in events:
                        events[ec] = []
                    events[ec].append(("end", sel_style))

        # build segments
        cols = sorted(events.keys())
        current_style = {}
        last = 0
        segs = []
        for col in cols:
            if col > last:
                segs.append((line[last:col], current_style.copy()))
            for typ, style in events[col]:
                if typ == "start":
                    current_style.update(style)
                else:
                    for k in list(style.keys()):
                        if k in current_style:
                            del current_style[k]
            last = col
        if last < len(line):
            segs.append((line[last:], current_style.copy()))
        if not segs:
            segs = [(line, {})]
        return segs

    # --- Editing and selection ---

    def _invalidate_size(self):
        # force re-measure on next layout
        pass

    def insert_text(self, index: Any, chars: str) -> None:
        """Public alias."""
        self.insert(index, chars)

    def delete_range(self, start: Any, end: Any = None) -> None:
        self.delete(start, end)

    # --- Input handling ---

    def on_click(self) -> None:
        pass

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self.contains(x, y) and not self._disabled:
            self._pressed = True
            line = int((y - self.y) / (self.font_size * 1.3))
            line = max(0, min(line, len(self._lines) - 1))
            col = self._approx_col_for_x(line, x, gui)
            pos = (line, col)
            self.mark_set("insert", pos)
            self._sel_start = pos
            self._sel_end = pos
            self._drag_anchor = pos
            return True
        return False

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        if self._disabled or not self._drag_anchor:
            return
        line = int((y - self.y) / (self.font_size * 1.3))
        line = max(0, min(line, len(self._lines) - 1))
        col = self._approx_col_for_x(line, x, gui)
        pos = (line, col)
        self.mark_set("insert", pos)
        self._sel_start = self._drag_anchor
        self._sel_end = pos
        self._set_selection_from_drag()

    def _set_selection_from_drag(self):
        if self._sel_start and self._sel_end:
            self.mark_set("sel.first", self._sel_start)
            self.mark_set("sel.last", self._sel_end)

    def _approx_col_for_x(
        self, line: int, mouse_x: float, gui: Optional["GUIManager"] = None
    ) -> int:
        if line >= len(self._lines):
            return 0
        text = self._lines[line]
        if not text:
            return 0
        text_x = self.x + 4
        rel_x = mouse_x - text_x
        if rel_x <= 0:
            return 0
        n = len(text)
        best = 0
        min_d = abs(rel_x)
        for i in range(1, n + 1):
            prefix = text[:i]
            if gui is not None:
                try:
                    w, _ = gui.measure_text(prefix, self.font_size)
                except Exception:
                    w = i * (self.font_size * 0.55)
            else:
                w = i * (self.font_size * 0.55)
            d = abs(w - rel_x)
            if d < min_d:
                min_d = d
                best = i
            if w > rel_x:
                break
        return min(n, best)

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        if self._disabled:
            return False

        ctrl = bool(mod & (pygame.KMOD_CTRL | pygame.KMOD_META))
        shift = bool(mod & pygame.KMOD_SHIFT)

        # similar ctrl hotkeys, adapted for lines
        if ctrl:
            if key == pygame.K_a:
                self._sel_start = (0, 0)
                last = len(self._lines) - 1
                self._sel_end = (last, len(self._lines[last]))
                self.mark_set("sel.first", self._sel_start)
                self.mark_set("sel.last", self._sel_end)
                self.mark_set("insert", self._sel_end)
                return True
            if key == pygame.K_c:
                if self._sel_start and self._sel_end:
                    txt = self.get("sel.first", "sel.last")
                    try:
                        pygame.scrap.init()
                        pygame.scrap.put(pygame.SCRAP_TEXT, txt.encode("utf-8"))
                    except Exception:
                        pass
                return True
            if key == pygame.K_v:
                try:
                    pygame.scrap.init()
                    data = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if data:
                        paste = data.decode("utf-8", errors="ignore").replace("\0", "")
                        if self._sel_start and self._sel_end:
                            self.delete("sel.first", "sel.last")
                        self.insert("insert", paste)
                except Exception:
                    pass
                return True
            if key == pygame.K_x:
                if self._sel_start and self._sel_end:
                    txt = self.get("sel.first", "sel.last")
                    try:
                        pygame.scrap.init()
                        pygame.scrap.put(pygame.SCRAP_TEXT, txt.encode("utf-8"))
                    except Exception:
                        pass
                    self.delete("sel.first", "sel.last")
                return True
            return False

        # movement and edit
        ins = self._marks.get("insert", (0, 0))
        line, col = ins

        if key == pygame.K_LEFT:
            if shift:
                if not self._sel_start:
                    self._sel_start = ins
                col = max(0, col - 1)
                if col == 0 and line > 0:
                    line -= 1
                    col = len(self._lines[line])
                new_ins = (line, col)
                self.mark_set("insert", new_ins)
                self._sel_end = new_ins
                self._set_selection_from_drag()
            else:
                if self._sel_start and self._sel_end:
                    self.mark_set("insert", min(self._sel_start, self._sel_end))
                    self._sel_start = self._sel_end = None
                    self.mark_unset("sel.first")
                    self.mark_unset("sel.last")
                else:
                    col = max(0, col - 1)
                    if col == 0 and line > 0:
                        line -= 1
                        col = len(self._lines[line])
                    self.mark_set("insert", (line, col))
            return True

        if key == pygame.K_RIGHT:
            if shift:
                if not self._sel_start:
                    self._sel_start = ins
                if col < len(self._lines[line]):
                    col += 1
                elif line < len(self._lines) - 1:
                    line += 1
                    col = 0
                new_ins = (line, col)
                self.mark_set("insert", new_ins)
                self._sel_end = new_ins
                self._set_selection_from_drag()
            else:
                if self._sel_start and self._sel_end:
                    self.mark_set("insert", max(self._sel_start, self._sel_end))
                    self._sel_start = self._sel_end = None
                    self.mark_unset("sel.first")
                    self.mark_unset("sel.last")
                else:
                    if col < len(self._lines[line]):
                        col += 1
                    elif line < len(self._lines) - 1:
                        line += 1
                        col = 0
                    self.mark_set("insert", (line, col))
            return True

        if key == pygame.K_UP:
            if shift:
                if not self._sel_start:
                    self._sel_start = ins
                if line > 0:
                    line -= 1
                    col = min(col, len(self._lines[line]))
                new_ins = (line, col)
                self.mark_set("insert", new_ins)
                self._sel_end = new_ins
                self._set_selection_from_drag()
            else:
                if self._sel_start:
                    self.mark_set("insert", min(self._sel_start, self._sel_end))
                    self._sel_start = self._sel_end = None
                if line > 0:
                    line -= 1
                    col = min(col, len(self._lines[line]))
                self.mark_set("insert", (line, col))
            return True

        if key == pygame.K_DOWN:
            if shift:
                if not self._sel_start:
                    self._sel_start = ins
                if line < len(self._lines) - 1:
                    line += 1
                    col = min(col, len(self._lines[line]))
                new_ins = (line, col)
                self.mark_set("insert", new_ins)
                self._sel_end = new_ins
                self._set_selection_from_drag()
            else:
                if self._sel_start:
                    self.mark_set("insert", max(self._sel_start, self._sel_end))
                    self._sel_start = self._sel_end = None
                if line < len(self._lines) - 1:
                    line += 1
                    col = min(col, len(self._lines[line]))
                self.mark_set("insert", (line, col))
            return True

        if key == pygame.K_HOME:
            if shift:
                if not self._sel_start:
                    self._sel_start = ins
                self._sel_end = (line, 0)
                self.mark_set("insert", self._sel_end)
                self._set_selection_from_drag()
            else:
                if self._sel_start:
                    self.mark_set("insert", (line, 0))
                    self._sel_start = self._sel_end = None
                else:
                    self.mark_set("insert", (line, 0))
            return True

        if key == pygame.K_END:
            if shift:
                if not self._sel_start:
                    self._sel_start = ins
                self._sel_end = (line, len(self._lines[line]))
                self.mark_set("insert", self._sel_end)
                self._set_selection_from_drag()
            else:
                if self._sel_start:
                    self.mark_set("insert", (line, len(self._lines[line])))
                    self._sel_start = self._sel_end = None
                else:
                    self.mark_set("insert", (line, len(self._lines[line])))
            return True

        if key == pygame.K_BACKSPACE:
            if self._sel_start and self._sel_end:
                self.delete("sel.first", "sel.last")
            elif self._pos_lt((0, 0), self._marks.get("insert", (0, 0))):
                ins = self._marks["insert"]
                if ins[1] > 0:
                    self.delete((ins[0], ins[1] - 1), ins)
                elif ins[0] > 0:
                    prev_line = ins[0] - 1
                    self._lines[prev_line] += self._lines[ins[0]]
                    del self._lines[ins[0]]
                    self.mark_set("insert", (prev_line, len(self._lines[prev_line])))
            self._sel_start = self._sel_end = None
            return True

        if key == pygame.K_DELETE:
            if self._sel_start and self._sel_end:
                self.delete("sel.first", "sel.last")
            else:
                ins = self._marks.get("insert", (0, 0))
                if ins[1] < len(self._lines[ins[0]]):
                    self.delete(ins, (ins[0], ins[1] + 1))
                elif ins[0] < len(self._lines) - 1:
                    self._lines[ins[0]] += self._lines[ins[0] + 1]
                    del self._lines[ins[0] + 1]
            self._sel_start = self._sel_end = None
            return True

        if key == pygame.K_RETURN:
            ins = self._marks.get("insert", (0, 0))
            if self._sel_start and self._sel_end:
                self.delete("sel.first", "sel.last")
                ins = self._marks.get("insert", (0, 0))
            left = self._lines[ins[0]][: ins[1]]
            right = self._lines[ins[0]][ins[1] :]
            self._lines[ins[0]] = left
            self._lines.insert(ins[0] + 1, right)
            self.mark_set("insert", (ins[0] + 1, 0))
            self._sel_start = self._sel_end = None
            return True

        if key == pygame.K_TAB:
            # insert tab or let GUI handle? For Text widget, insert a tab char
            ins = self._marks.get("insert", (0, 0))
            if self._sel_start and self._sel_end:
                self.delete("sel.first", "sel.last")
            self.insert("insert", "\t")
            return True  # consume so doesn't always focus change

        if char and ord(char) >= 32:
            if self._sel_start and self._sel_end:
                self.delete("sel.first", "sel.last")
            self.insert("insert", char)
            return True

        return False

    def on_key_state(self, pressed) -> bool:
        """Responsive held-key input for Text (arrows, backspace, delete)."""
        if self._disabled or not self._focused:
            return False
        now = pygame.time.get_ticks()
        mod = pygame.key.get_mods()

        # Nav + edit keys that benefit from polling state for smooth repeat
        repeatables = (
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_UP,
            pygame.K_DOWN,
            pygame.K_HOME,
            pygame.K_END,
            pygame.K_BACKSPACE,
            pygame.K_DELETE,
        )

        for k in list(self._next_repeat.keys()):
            if not pressed[k]:
                self._next_repeat.pop(k, None)

        acted = False
        for k in repeatables:
            if not pressed[k]:
                continue
            nxt = self._next_repeat.get(k, 0)
            if nxt == 0:
                self._next_repeat[k] = now + self._repeat_delay
                if self.on_key(k, "", mod):
                    acted = True
                continue
            if now >= nxt:
                if self.on_key(k, "", mod):
                    self._next_repeat[k] = now + self._repeat_interval
                    acted = True
        return acted

    def _get_line_segments(self, line_idx: int, line: str) -> list[tuple[str, dict]]:
        """Return [(text, style), ...] for the line, applying tags and selection."""
        if not line:
            return [("", {})]
        segments: list[tuple[str, dict]] = []
        current_style = {"foreground": (0.9, 0.9, 0.9, 1.0)}
        events: dict[int, list] = {}
        for tag, info in self._tags.items():
            for (sl, sc), (el, ec) in info.get("ranges", []):
                if sl <= line_idx <= el:
                    sc_ = sc if sl == line_idx else 0
                    ec_ = ec if el == line_idx else len(line)
                    if sc_ < ec_:
                        style = info.get("config", {}).copy()
                        if sc_ not in events:
                            events[sc_] = []
                        events[sc_].append(("start", style))
                        if ec_ not in events:
                            events[ec_] = []
                        events[ec_].append(("end", style))
        if self._sel_start and self._sel_end:
            ss = min(self._sel_start, self._sel_end)
            se = max(self._sel_start, self._sel_end)
            if ss[0] <= line_idx <= se[0]:
                sc = ss[1] if ss[0] == line_idx else 0
                ec = se[1] if se[0] == line_idx else len(line)
                if sc < ec:
                    sel_style = {"background": (0.25, 0.45, 0.75, 0.5)}
                    if sc not in events:
                        events[sc] = []
                    events[sc].append(("start", sel_style))
                    if ec not in events:
                        events[ec] = []
                    events[ec].append(("end", sel_style))
        cols = sorted(events.keys())
        last = 0
        for col in cols:
            if col > last:
                segments.append((line[last:col], current_style.copy()))
            for typ, st in events.get(col, []):
                if typ == "start":
                    current_style.update(st)
                else:
                    for k in list(st.keys()):
                        current_style.pop(k, None)
            last = col
        if last < len(line):
            segments.append((line[last:], current_style.copy()))
        if not segments:
            segments = [(line, {"foreground": (0.9, 0.9, 0.9, 1.0)})]
        return segments


class Listbox(Widget):
    """Scrollable list of selectable items (Tkinter Listbox like).

    - items: list of str
    - selectmode: 'single' or 'browse' (single), 'multiple'
    - height: visible lines
    - .insert(index, item), .delete(index), .get(index), curselection()
    - selection via click, arrows when focused
    - grid compatible, nested ok
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        items: Optional[list[str]] = None,
        height: int = 5,
        selectmode: str = "browse",  # "browse" or "multiple"
        font_size: int = 14,
    ) -> None:
        super().__init__(parent)
        self.items: list[str] = items or []
        self.visible_lines = height
        self.selectmode = selectmode
        self.selected: list[int] = []  # list of indices
        self.font_size = font_size
        self._scroll: int = 0  # first visible item
        self._min_height = 20
        self.yscrollcommand = None
        # held repeat for arrows
        self._next_repeat: dict[int, int] = {}
        self._repeat_delay = 300
        self._repeat_interval = 50

    def can_focus(self) -> bool:
        return not self._disabled

    def yview(self, *args):
        if args:
            if args[0] == "moveto":
                self.yview_moveto(args[1])
            elif args[0] == "scroll":
                self.yview_scroll(*args[1:])
            return
        total = max(1, len(self.items))
        first = self._scroll / total
        last = min(1.0, (self._scroll + self.visible_lines) / total)
        if self.yscrollcommand:
            try:
                self.yscrollcommand(first, last)
            except Exception:
                pass
        return first, last

    def yview_moveto(self, fraction):
        total = max(1, len(self.items))
        self._scroll = max(
            0, min(int(fraction * total), max(0, total - self.visible_lines))
        )
        self.yview()

    def yview_scroll(self, number, what="units"):
        if what == "units":
            delta = int(number)
        else:
            delta = int(number) * self.visible_lines
        self._scroll = max(
            0, min(self._scroll + delta, max(0, len(self.items) - self.visible_lines))
        )
        self.yview()

    def insert(self, index: int, item: str) -> None:
        if index < 0 or index > len(self.items):
            index = len(self.items)
        self.items.insert(index, item)
        # adjust selection
        self.selected = [i + 1 if i >= index else i for i in self.selected]

    def delete(self, index: int) -> None:
        if 0 <= index < len(self.items):
            del self.items[index]
            self.selected = [i for i in self.selected if i != index]
            self.selected = [i - 1 if i > index else i for i in self.selected]

    def get(self, index: int) -> str:
        if 0 <= index < len(self.items):
            return self.items[index]
        return ""

    def curselection(self) -> list[int]:
        return sorted(self.selected)

    def select(self, index: int) -> None:
        if 0 <= index < len(self.items):
            if self.selectmode in ("browse", "single"):
                self.selected = [index]
            else:
                if index not in self.selected:
                    self.selected.append(index)

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if not self.items:
            w = 100
        else:
            if gui:
                w = max(
                    gui.measure_text(str(item), self.font_size)[0]
                    for item in self.items
                )
            else:
                w = max(len(str(item)) for item in self.items) * (self.font_size * 0.55)
        h = self.visible_lines * (self.font_size * 1.3) + 4
        return w + 8, max(h, self._min_height)

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self.contains(x, y) and not self._disabled:
            self._pressed = True
            line_h = self.font_size * 1.3
            idx = int((y - self.y) / line_h) + self._scroll
            if 0 <= idx < len(self.items):
                if self.selectmode in ("browse", "single"):
                    self.selected = [idx]
                else:
                    if idx in self.selected:
                        self.selected.remove(idx)
                    else:
                        self.selected.append(idx)
                # clamp scroll
                if idx < self._scroll:
                    self._scroll = idx
                elif idx >= self._scroll + self.visible_lines:
                    self._scroll = idx - self.visible_lines + 1
            self.yview()
            return True
        return False

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        if self._disabled or not self.items:
            return False
        if not self.selected:
            self.selected = [0]
        idx = (
            self.selected[0]
            if self.selectmode in ("browse", "single")
            else self.selected[0]
            if self.selected
            else 0
        )

        if key == pygame.K_UP:
            idx = max(0, idx - 1)
            self.select(idx)
            if idx < self._scroll:
                self._scroll = idx
            self.yview()
            return True
        if key == pygame.K_DOWN:
            idx = min(len(self.items) - 1, idx + 1)
            self.select(idx)
            if idx >= self._scroll + self.visible_lines:
                self._scroll = idx - self.visible_lines + 1
            self.yview()
            return True
        if key == pygame.K_HOME:
            self.select(0)
            self._scroll = 0
            self.yview()
            return True
        if key == pygame.K_END:
            last = len(self.items) - 1
            self.select(last)
            if last >= self._scroll + self.visible_lines:
                self._scroll = last - self.visible_lines + 1
            self.yview()
            return True
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.selectmode == "multiple":
                if idx in self.selected:
                    self.selected.remove(idx)
                else:
                    self.selected.append(idx)
            self.yview()
            return True
        self.yview()
        return False

    def on_key_state(self, pressed) -> bool:
        if self._disabled or not self._focused or not self.items:
            return False
        now = pygame.time.get_ticks()
        mod = pygame.key.get_mods()
        repeatables = (pygame.K_UP, pygame.K_DOWN, pygame.K_HOME, pygame.K_END)
        for k in list(self._next_repeat.keys()):
            if not pressed[k]:
                self._next_repeat.pop(k, None)
        acted = False
        for k in repeatables:
            if not pressed[k]:
                continue
            nxt = self._next_repeat.get(k, 0)
            if nxt == 0:
                self._next_repeat[k] = now + self._repeat_delay
                if self.on_key(k, "", mod):
                    acted = True
                continue
            if now >= nxt:
                if self.on_key(k, "", mod):
                    self._next_repeat[k] = now + self._repeat_interval
                    acted = True
        return acted

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        r.draw_rect(self.x, self.y, self.width, self.height, (0.1, 0.1, 0.12, 1.0))
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.25, 0.25, 0.28, 1.0)
        )

        if not self.items:
            return
        line_h = self.font_size * 1.3
        text_x = self.x + 4
        for i in range(self.visible_lines):
            idx = i + self._scroll
            if idx >= len(self.items):
                break
            y = self.y + i * line_h + 2
            if y + line_h > self.y + self.height:
                break
            if idx in self.selected:
                r.draw_rect(
                    self.x + 1, y, self.width - 2, line_h - 2, (0.2, 0.4, 0.7, 0.6)
                )
            r.draw_text(
                self.items[idx],
                text_x,
                y,
                color=(0.9, 0.9, 0.9, 1.0),
                font_size=self.font_size,
            )


class Combobox(Widget):
    """Dropdown combobox (Entry + Listbox popup), Tkinter like.

    - values: list[str]
    - current text or index
    - .get(), .set(value)
    - clicking arrow toggles dropdown list (drawn below)
    - select from list sets value and closes
    - supports typing? basic (or readonly)
    - grid/nested ok (dropdown may overlay)
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        values: Optional[list[str]] = None,
        width: int = 15,
        font_size: int = 14,
        state: str = "normal",  # "normal" or "readonly"
    ) -> None:
        super().__init__(parent)
        self.values: list[str] = values or []
        self._text: str = self.values[0] if self.values else ""
        self.width_chars = width
        self.font_size = font_size
        self.state = state
        self._open: bool = False
        self._min_height = 24
        self._arrow_w = 18

    def can_focus(self) -> bool:
        return not self._disabled

    def get(self) -> str:
        return self._text

    def set(self, value: str) -> None:
        if value in self.values or self.state == "normal":
            self._text = value
        self._open = False

    def contains(self, x: float, y: float) -> bool:
        if super().contains(x, y):
            return True
        if getattr(self, "_open", False) and self.values:
            line_h = self.font_size * 1.3
            drop_h = min(len(self.values), 8) * line_h
            if (
                self.x <= x < self.x + self.width
                and self.y + self.height <= y < self.y + self.height + drop_h
            ):
                return True
        return False

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui:
            w = gui.measure_text("W" * self.width_chars, self.font_size)[0]
        else:
            w = self.width_chars * (self.font_size * 0.55)
        return w + self._arrow_w + 8, self._min_height

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self._disabled:
            return False
        rel_y = y - self.y
        if rel_y < self.height:
            # main area
            self._pressed = True
            if x >= self.x + self.width - self._arrow_w:
                self._open = not self._open
            else:
                if self.state == "normal":
                    self._open = not self._open
            return True
        elif self._open:
            # dropdown area
            line_h = self.font_size * 1.3
            drop_y = self.y + self.height
            idx = int((y - drop_y) / line_h)
            if 0 <= idx < len(self.values):
                self.set(self.values[idx])
                return True
            else:
                self._open = False
                return True
        return False

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        if self._disabled:
            return False
        if self.state == "readonly" and not self._open:
            if key in (pygame.K_DOWN, pygame.K_SPACE, pygame.K_RETURN):
                self._open = True
                return True
            return False
        # basic: if open use arrows, else type if normal
        if self._open:
            if key == pygame.K_UP:
                idx = max(
                    0,
                    (self.values.index(self._text) if self._text in self.values else 0)
                    - 1,
                )
                self.set(self.values[idx])
                return True
            if key == pygame.K_DOWN:
                idx = min(
                    len(self.values) - 1,
                    (self.values.index(self._text) if self._text in self.values else 0)
                    + 1,
                )
                self.set(self.values[idx])
                return True
            if key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self._open = False
                return True
        else:
            if self.state == "normal":
                # delegate like entry, but simple
                if key == pygame.K_BACKSPACE and self._text:
                    self._text = self._text[:-1]
                    return True
                if char and ord(char) >= 32:
                    self._text += char
                    return True
        return False

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        # main box like entry
        r.draw_rect(self.x, self.y, self.width, self.height, (0.12, 0.12, 0.13, 1.0))
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.25, 0.25, 0.28, 1.0)
        )
        # text
        r.draw_text(
            self._text,
            self.x + 4,
            self.y + 3,
            color=(0.9, 0.9, 0.9, 1.0),
            font_size=self.font_size,
        )
        # arrow box
        ax = self.x + self.width - self._arrow_w
        r.draw_rect(ax, self.y, self._arrow_w, self.height, (0.2, 0.2, 0.22, 1.0))
        # simple down arrow
        midx = ax + self._arrow_w / 2
        r.draw_line(midx - 4, self.y + 8, midx + 4, self.y + 8, 1, (0.8, 0.8, 0.8, 1))
        r.draw_line(midx - 4, self.y + 8, midx, self.y + 14, 1, (0.8, 0.8, 0.8, 1))
        r.draw_line(midx + 4, self.y + 8, midx, self.y + 14, 1, (0.8, 0.8, 0.8, 1))

        if self._open and self.values:
            line_h = self.font_size * 1.3
            drop_h = min(len(self.values), 8) * line_h
            drop_y = self.y + self.height
            r.draw_rect(self.x, drop_y, self.width, drop_h, (0.1, 0.1, 0.12, 1.0))
            r.draw_rect_border(
                self.x, drop_y, self.width, drop_h, 1.0, (0.25, 0.25, 0.28, 1.0)
            )
            for i, val in enumerate(self.values):
                if i * line_h > drop_h:
                    break
                yy = drop_y + i * line_h + 2
                if val == self._text:
                    r.draw_rect(
                        self.x + 1, yy, self.width - 2, line_h - 2, (0.2, 0.4, 0.7, 0.5)
                    )
                r.draw_text(
                    val,
                    self.x + 4,
                    yy,
                    color=(0.9, 0.9, 0.9, 1.0),
                    font_size=self.font_size,
                )


class Spinbox(Widget):
    """Spinbox widget (number or values list with up/down), Tkinter like.

    - Can use from_, to, increment or values list
    - Clicking arrows changes value
    - Typing allowed if numeric
    - .get(), set()
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        from_: float = 0,
        to: float = 100,
        increment: float = 1,
        values: Optional[list[str]] = None,
        width: int = 8,
        font_size: int = 14,
    ) -> None:
        super().__init__(parent)
        self.from_ = from_
        self.to = to
        self.increment = increment
        self.values = values
        self._value: str = str(from_) if not values else values[0]
        self.width_chars = width
        self.font_size = font_size
        self._min_height = 24
        self._arrow_h = 10  # half height for each arrow
        # repeat state (up/down fast spin)
        self._next_repeat: dict[int, int] = {}
        self._repeat_delay = 200
        self._repeat_interval = 80

    def can_focus(self) -> bool:
        return not self._disabled

    def get(self) -> str:
        return self._value

    def set(self, val: str) -> None:
        if self.values:
            if val in self.values:
                self._value = val
        else:
            try:
                f = float(val)
                if self.from_ <= f <= self.to:
                    self._value = str(f)
            except Exception:
                pass

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui:
            w = gui.measure_text("W" * self.width_chars, self.font_size)[0]
        else:
            w = self.width_chars * (self.font_size * 0.55)
        return w + 16, self._min_height

    def _change(self, up: bool):
        if self.values:
            try:
                idx = self.values.index(self._value)
                new_idx = max(0, min(len(self.values) - 1, idx + (1 if up else -1)))
                self._value = self.values[new_idx]
            except Exception:
                pass
        else:
            try:
                f = float(self._value) + (self.increment if up else -self.increment)
                f = max(self.from_, min(self.to, f))
                self._value = str(f)
            except Exception:
                pass

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if not self.contains(x, y) or self._disabled:
            return False
        self._pressed = True
        # arrows on right
        if x > self.x + self.width - 16:
            up = y < self.y + self.height / 2
            self._change(up)
            return True
        # else focus for edit if want
        return True

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        if self._disabled:
            return False
        if key == pygame.K_UP:
            self._change(True)
            return True
        if key == pygame.K_DOWN:
            self._change(False)
            return True
        if key == pygame.K_BACKSPACE and self._value:
            self._value = self._value[:-1]
            return True
        if char and ord(char) >= 32:
            # append if numeric?
            new = self._value + char
            if self.values or (
                new.replace(".", "", 1).lstrip("-").isdigit() or new == "-"
            ):
                self._value = new
            return True
        return False

    def on_key_state(self, pressed) -> bool:
        if self._disabled or not self._focused:
            return False
        now = pygame.time.get_ticks()
        mod = pygame.key.get_mods()
        # For spin, fast continuous change feels best; use short interval
        for k in (pygame.K_UP, pygame.K_DOWN):
            if pressed[k]:
                nxt = self._next_repeat.get(k, 0)
                if nxt == 0 or now >= nxt:
                    self.on_key(k, "", mod)
                    self._next_repeat[k] = now + self._repeat_interval
                    # also clear other
                    other = pygame.K_DOWN if k == pygame.K_UP else pygame.K_UP
                    self._next_repeat.pop(other, None)
                    return True
        # clear if released
        for k in (pygame.K_UP, pygame.K_DOWN):
            if not pressed[k]:
                self._next_repeat.pop(k, None)
        return False

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        r.draw_rect(self.x, self.y, self.width, self.height, (0.12, 0.12, 0.13, 1.0))
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.25, 0.25, 0.28, 1.0)
        )
        # text
        r.draw_text(
            self._value,
            self.x + 4,
            self.y + 3,
            color=(0.9, 0.9, 0.9, 1.0),
            font_size=self.font_size,
        )
        # arrows
        ax = self.x + self.width - 14
        # up arrow
        r.draw_line(ax + 3, self.y + 6, ax + 7, self.y + 2, 1, (0.7, 0.7, 0.7, 1))
        r.draw_line(ax + 7, self.y + 2, ax + 11, self.y + 6, 1, (0.7, 0.7, 0.7, 1))
        # down
        r.draw_line(
            ax + 3,
            self.y + self.height - 6,
            ax + 7,
            self.y + self.height - 2,
            1,
            (0.7, 0.7, 0.7, 1),
        )
        r.draw_line(
            ax + 7,
            self.y + self.height - 2,
            ax + 11,
            self.y + self.height - 6,
            1,
            (0.7, 0.7, 0.7, 1),
        )


class Canvas(Widget):
    """Canvas widget - drawing surface for shapes, lines, text, images, custom graphics.

    Tkinter Canvas inspired, integrated with Grimoire2D Renderer.
    Supports grid layout, nesting in Frames, scrolling with Scrollbar (xview/yview).

    Item creation (returns item id):
      - create_line(x1,y1, x2,y2, ..., fill=..., width=1, tags=..., dash=...)
      - create_rectangle(x1,y1,x2,y2, fill=..., outline=..., width=..., tags=...)
      - create_oval(x1,y1,x2,y2, ...)
      - create_polygon(x1,y1,..., fill=..., outline=..., tags=...)
      - create_text(x, y, text=..., fill=..., font_size=14, anchor='nw', tags=...)
      - create_image(x, y, texture=moderngl.Texture, width=None, height=None, tags=...)  # uses draw_sprite
      - create_custom(draw_func, tags=...)  # draw_func(renderer, origin_x, origin_y) where screen_pos = origin + logical_canvas_coord

    Other methods:
      - delete(item or 'all' or tag)
      - coords(item, *new_coords) or get
      - itemconfig(item, **options) / itemcget
      - tag_add(tag, item), tag_remove, find_withtag(tag)
      - move(item, dx, dy)
      - bbox(item)
      - xview / yview for scrolling (integrates with Scrollbar)
      - canvasx/y (screen to canvas coords)
      - bind_item or tag_bind (basic event callbacks on items)

    Scrolling: set scrollregion=(x0,y0,x1,y1) or it auto from content.
    Use with Scrollbar: sb = Scrollbar(..., command=canvas.yview); canvas.yscrollcommand = sb.set

    All in virtual space. Good for game tools, editors, diagrams.
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        width: float = 400,
        height: float = 300,
        bg: tuple[float, ...] = (0.15, 0.15, 0.18, 1.0),
        scrollregion: Optional[tuple[float, float, float, float]] = None,
    ) -> None:
        super().__init__(parent)
        self._width = width
        self._height = height
        self.bg = bg
        self.scrollregion = scrollregion
        self._items: dict[int, dict] = {}
        self._order: list[int] = []  # creation/draw order
        self._tags: dict[str, set[int]] = {}  # tag -> set of item ids
        self._next_id = 1
        self._x_scroll = 0.0
        self._y_scroll = 0.0
        self.xscrollcommand = None
        self.yscrollcommand = None
        self._item_bindings: dict[int, dict] = {}  # item_id -> {event: callback}
        self._tag_bindings: dict[str, dict] = {}  # tag -> {event: callback}
        self._min_size = (50, 50)
        self.font_size = 14
        self._drag_last: Optional[tuple[float, float]] = None

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        """Return requested size as preferred (for grid layout)."""
        return self._width, self._height

    def can_focus(self) -> bool:
        return not self._disabled

    # --- Item creation ---

    def _add_item(self, item_type: str, coords: list[float], options: dict) -> int:
        iid = self._next_id
        self._next_id += 1
        tags = set(options.pop("tags", []) or [])
        if isinstance(tags, str):
            tags = {tags}
        item = {
            "type": item_type,
            "coords": list(coords),
            "options": options,
            "tags": tags,
        }
        self._items[iid] = item
        self._order.append(iid)
        for tag in tags:
            if tag not in self._tags:
                self._tags[tag] = set()
            self._tags[tag].add(iid)
        self._invalidate_scrollregion()
        return iid

    def create_line(self, *coords: float, **options: Any) -> int:
        if len(coords) < 4 or len(coords) % 2 != 0:
            raise ValueError("create_line needs at least 2 points (x1,y1,x2,y2,...)")
        return self._add_item("line", list(coords), options)

    def create_rectangle(
        self, x1: float, y1: float, x2: float, y2: float, **options: Any
    ) -> int:
        return self._add_item("rectangle", [x1, y1, x2, y2], options)

    def create_oval(
        self, x1: float, y1: float, x2: float, y2: float, **options: Any
    ) -> int:
        return self._add_item("oval", [x1, y1, x2, y2], options)

    def create_polygon(self, *coords: float, **options: Any) -> int:
        if len(coords) < 6 or len(coords) % 2 != 0:
            raise ValueError("create_polygon needs at least 3 points")
        return self._add_item("polygon", list(coords), options)

    def create_text(self, x: float, y: float, text: str = "", **options: Any) -> int:
        opts = dict(options)
        opts["text"] = text
        return self._add_item("text", [x, y], opts)

    def create_image(
        self,
        x: float,
        y: float,
        texture: Any = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        **options: Any,
    ) -> int:
        opts = dict(options)
        opts["texture"] = texture
        opts["width"] = width
        opts["height"] = height
        return self._add_item("image", [x, y], opts)

    def create_custom(self, draw_func: Callable, **options: Any) -> int:
        """Custom item: draw_func(renderer, offset_x, offset_y)"""
        opts = dict(options)
        opts["draw"] = draw_func
        return self._add_item("custom", [], opts)

    # --- Manipulation ---

    def delete(self, item: Any) -> None:
        if item == "all":
            self._items.clear()
            self._order.clear()
            self._tags.clear()
            self._item_bindings.clear()
            self._tag_bindings.clear()
            return
        ids = self._find_ids(item)
        for iid in ids:
            if iid in self._items:
                tags = self._items[iid].get("tags", set())
                for t in tags:
                    self._tags.get(t, set()).discard(iid)
                self._items.pop(iid, None)
                if iid in self._order:
                    self._order.remove(iid)
                self._item_bindings.pop(iid, None)
        self._invalidate_scrollregion()

    def coords(self, item: Any, *new_coords: float) -> Optional[list[float]]:
        ids = self._find_ids(item)
        if not ids:
            return None
        iid = ids[0]
        itemd = self._items[iid]
        if new_coords:
            itemd["coords"] = list(new_coords)
            self._invalidate_scrollregion()
            return None
        return list(itemd.get("coords", []))

    def itemconfig(self, item: Any, **options: Any) -> None:
        ids = self._find_ids(item)
        for iid in ids:
            if iid in self._items:
                self._items[iid]["options"].update(options)
                if "tags" in options:
                    newtags = set(options["tags"]) if options["tags"] else set()
                    oldtags = self._items[iid].get("tags", set())
                    for t in oldtags - newtags:
                        self._tags.get(t, set()).discard(iid)
                    for t in newtags - oldtags:
                        if t not in self._tags:
                            self._tags[t] = set()
                        self._tags[t].add(iid)
                    self._items[iid]["tags"] = newtags

    def itemcget(self, item: Any, option: str) -> Any:
        ids = self._find_ids(item)
        if not ids:
            return None
        return self._items[ids[0]]["options"].get(option)

    def tag_add(self, tag: str, *items: Any) -> None:
        if tag not in self._tags:
            self._tags[tag] = set()
        for it in items:
            for iid in self._find_ids(it):
                self._tags[tag].add(iid)
                self._items.setdefault(iid, {}).setdefault("tags", set()).add(tag)

    def tag_remove(self, tag: str, *items: Any) -> None:
        if tag not in self._tags:
            return
        for it in items:
            for iid in self._find_ids(it):
                self._tags[tag].discard(iid)
                if iid in self._items:
                    self._items[iid].get("tags", set()).discard(tag)

    def find_withtag(self, tag: str) -> list[int]:
        return list(self._tags.get(tag, set()))

    def move(self, item: Any, dx: float, dy: float) -> None:
        for iid in self._find_ids(item):
            if iid in self._items:
                coords = self._items[iid]["coords"]
                for i in range(len(coords)):
                    if i % 2 == 0:
                        coords[i] += dx
                    else:
                        coords[i] += dy
        self._invalidate_scrollregion()

    def bbox(self, item: Any = "all") -> Optional[tuple[float, float, float, float]]:
        ids = self._find_ids(item) if item != "all" else list(self._items.keys())
        if not ids:
            return None
        minx, miny, maxx, maxy = (
            float("inf"),
            float("inf"),
            float("-inf"),
            float("-inf"),
        )
        for iid in ids:
            if iid not in self._items:
                continue
            cs = self._items[iid].get("coords", [])
            for i in range(0, len(cs), 2):
                minx = min(minx, cs[i])
                miny = min(miny, cs[i + 1])
                maxx = max(maxx, cs[i])
                maxy = max(maxy, cs[i + 1])
        if minx == float("inf"):
            return None
        return (minx, miny, maxx, maxy)

    # --- Scrolling ---

    def canvasx(self, screen_x: float) -> float:
        return screen_x - self.x + self._x_scroll

    def canvasy(self, screen_y: float) -> float:
        return screen_y - self.y + self._y_scroll

    def _get_scrollregion(self) -> tuple[float, float, float, float]:
        if self.scrollregion:
            return self.scrollregion
        bb = self.bbox("all")
        if bb:
            return bb
        return (0, 0, self._width, self._height)

    def xview(self, *args: Any) -> Optional[tuple[float, float]]:
        sr = self._get_scrollregion()
        total_w = max(1.0, sr[2] - sr[0])
        if args:
            if args[0] == "moveto":
                self._x_scroll = sr[0] + float(args[1]) * total_w
            elif args[0] == "scroll":
                n, what = args[1], args[2]
                if what == "units":
                    self._x_scroll += float(n) * 10  # arbitrary unit
                else:
                    self._x_scroll += float(n) * (self.width or total_w * 0.1)
            self._clamp_scroll()
            if self.xscrollcommand:
                try:
                    self.xscrollcommand(*self.xview())
                except Exception:
                    pass
            return
        # return fraction
        view_w = self.width if self.width > 0 else self._width
        if view_w <= 0:
            view_w = total_w * 0.5
        first = max(0.0, min(1.0, (self._x_scroll - sr[0]) / total_w))
        last = min(1.0, first + view_w / total_w)
        if self.xscrollcommand:
            try:
                self.xscrollcommand(first, last)
            except Exception:
                pass
        return first, last

    def yview(self, *args: Any) -> Optional[tuple[float, float]]:
        sr = self._get_scrollregion()
        total_h = max(1.0, sr[3] - sr[1])
        if args:
            if args[0] == "moveto":
                self._y_scroll = sr[1] + float(args[1]) * total_h
            elif args[0] == "scroll":
                n, what = args[1], args[2]
                if what == "units":
                    self._y_scroll += float(n) * 10
                else:
                    self._y_scroll += float(n) * (self.height or total_h * 0.1)
            self._clamp_scroll()
            if self.yscrollcommand:
                try:
                    self.yscrollcommand(*self.yview())
                except Exception:
                    pass
            return
        view_h = self.height if self.height > 0 else self._height
        if view_h <= 0:
            view_h = total_h * 0.5
        first = max(0.0, min(1.0, (self._y_scroll - sr[1]) / total_h))
        last = min(1.0, first + view_h / total_h)
        if self.yscrollcommand:
            try:
                self.yscrollcommand(first, last)
            except Exception:
                pass
        return first, last

    def _clamp_scroll(self):
        sr = self._get_scrollregion()
        vw = self.width if self.width > 0 else self._width or 1
        vh = self.height if self.height > 0 else self._height or 1
        self._x_scroll = max(sr[0], min(self._x_scroll, sr[2] - vw))
        self._y_scroll = max(sr[1], min(self._y_scroll, sr[3] - vh))

    def _invalidate_scrollregion(self):
        if not self.scrollregion:
            # will recompute in _get
            pass

    # --- Drawing ---

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        # bg
        r.draw_rect(self.x, self.y, self.width, self.height, self.bg)
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.3, 0.3, 0.35, 1.0)
        )

        ox = self._x_scroll
        oy = self._y_scroll
        base_x = self.x
        base_y = self.y
        clip_l, clip_t = base_x, base_y
        clip_r, clip_b = base_x + self.width, base_y + self.height

        for iid in self._order:
            if iid not in self._items:
                continue
            item = self._items[iid]
            t = item["type"]
            coords = item["coords"]
            opts = item["options"]

            if t == "line" and len(coords) >= 4:
                # support polyline
                col = opts.get("fill", opts.get("outline", (0.8, 0.8, 0.8, 1.0)))
                w = opts.get("width", 1.0)
                for j in range(0, len(coords) - 2, 2):
                    x1 = base_x + (coords[j] - ox)
                    y1 = base_y + (coords[j + 1] - oy)
                    x2 = base_x + (coords[j + 2] - ox)
                    y2 = base_y + (coords[j + 3] - oy)
                    # simple clip check
                    if not self._rects_overlap(
                        x1, y1, x2, y2, clip_l, clip_t, clip_r, clip_b
                    ):
                        continue
                    r.draw_line(x1, y1, x2, y2, w, col)
            elif t == "rectangle" and len(coords) >= 4:
                x1 = base_x + (coords[0] - ox)
                y1 = base_y + (coords[1] - oy)
                x2 = base_x + (coords[2] - ox)
                y2 = base_y + (coords[3] - oy)
                w, h = x2 - x1, y2 - y1
                if w < 0:
                    x1, x2, w = x2, x1, -w
                if h < 0:
                    y1, y2, h = y2, y1, -h
                fill = opts.get("fill")
                outline = opts.get("outline")
                lw = opts.get("width", 1.0)
                if fill:
                    r.draw_rect(x1, y1, w, h, fill)
                if outline:
                    r.draw_rect_border(x1, y1, w, h, lw, outline)
            elif t == "oval" and len(coords) >= 4:
                x1 = base_x + (coords[0] - ox)
                y1 = base_y + (coords[1] - oy)
                x2 = base_x + (coords[2] - ox)
                y2 = base_y + (coords[3] - oy)
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                rx, ry = abs(x2 - x1) / 2, abs(y2 - y1) / 2
                fill = opts.get("fill")
                outline = opts.get("outline")
                lw = opts.get("width", 1.0)
                if fill:
                    r.draw_ellipse(cx, cy, rx, ry, fill)
                if outline:
                    # approx ring (for circles/ovals)
                    r.draw_ring(cx, cy, max(rx, ry), lw, outline)
            elif t == "polygon" and len(coords) >= 6:
                poly_coords: list[tuple[float, float]] = []
                for j in range(0, len(coords), 2):
                    poly_coords.append(
                        (base_x + coords[j] - ox, base_y + coords[j + 1] - oy)
                    )
                fill = opts.get("fill")
                outline = opts.get("outline")
                lw = opts.get("width", 1.0)
                if fill:
                    r.draw_polygon(poly_coords, fill)
                if outline:
                    if len(poly_coords) >= 3:
                        r.draw_polyline(poly_coords + [poly_coords[0]], lw, outline)
                    else:
                        r.draw_polyline(poly_coords, lw, outline)
            elif t == "text":
                tx = base_x + (coords[0] - ox)
                ty = base_y + (coords[1] - oy)
                txt = opts.get("text", "")
                fill = opts.get("fill", (0.9, 0.9, 0.9, 1.0))
                fsize = opts.get("font_size", self.font_size)
                anchor = opts.get("anchor", "nw")
                tw, th = (
                    gui.measure_text(txt, font_size=fsize)
                    if gui
                    else (len(txt) * fsize * 0.5, fsize)
                )
                if anchor == "center":
                    tx -= tw / 2
                    ty -= th / 2
                elif anchor == "ne":
                    tx -= tw
                elif anchor == "sw":
                    ty -= th
                elif anchor == "se":
                    tx -= tw
                    ty -= th
                # basic n/s etc omitted for brevity
                r.draw_text(txt, tx, ty, color=fill, font_size=fsize)
            elif t == "image" and "texture" in opts and opts["texture"]:
                tx = base_x + (coords[0] - ox)
                ty = base_y + (coords[1] - oy)
                tex = opts["texture"]
                iw = opts.get("width") or getattr(tex, "width", 32)
                ih = opts.get("height") or getattr(tex, "height", 32)
                r.draw_sprite(tex, tx, ty, iw, ih)
            elif t == "custom" and "draw" in opts:
                try:
                    # origin so that logical_canvas + origin gives screen coord
                    origin_x = base_x - ox
                    origin_y = base_y - oy
                    opts["draw"](r, origin_x, origin_y)
                except Exception:
                    pass

    def _rects_overlap(self, x1, y1, x2, y2, cl, ct, cr, cb) -> bool:
        # rough for lines etc
        return not (
            max(x1, x2) < cl or min(x1, x2) > cr or max(y1, y2) < ct or min(y1, y2) > cb
        )

    # --- Input / events (basic) ---

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if not self.contains(x, y) or self._disabled:
            return False
        self._pressed = True
        self._drag_last = (x, y)
        cx = self.canvasx(x)
        cy = self.canvasy(y)
        # find closest for possible binding dispatch
        closest = self.find_closest(cx, cy)
        if closest:
            self._dispatch_event(closest, "click", (x, y, button))
        return True

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        # Canvas can consume some keys if wanted, e.g. arrows for scroll
        if key == pygame.K_LEFT:
            self._x_scroll -= 10
            self.xview()
            return True
        if key == pygame.K_RIGHT:
            self._x_scroll += 10
            self.xview()
            return True
        if key == pygame.K_UP:
            self._y_scroll -= 10
            self.yview()
            return True
        if key == pygame.K_DOWN:
            self._y_scroll += 10
            self.yview()
            return True
        return False

    def on_key_state(self, pressed) -> bool:
        if not self._focused:
            return False
        # Simple: arrows while held continuously scroll the canvas view
        moved = False
        if pressed[pygame.K_LEFT]:
            self._x_scroll -= 10
            moved = True
        if pressed[pygame.K_RIGHT]:
            self._x_scroll += 10
            moved = True
        if pressed[pygame.K_UP]:
            self._y_scroll -= 10
            moved = True
        if pressed[pygame.K_DOWN]:
            self._y_scroll += 10
            moved = True
        if moved:
            self.yview()
            return True
        return False

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        """Pan the canvas view when dragging inside it (common for tools)."""
        if self._disabled or not self._pressed or self._drag_last is None:
            return
        lx, ly = self._drag_last
        dx = x - lx
        dy = y - ly
        self._x_scroll -= dx
        self._y_scroll -= dy
        self._drag_last = (x, y)
        self.xview()
        self.yview()

    def on_mouse_release(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        self._pressed = False
        self._drag_last = None
        return False

    def find_closest(self, x: float, y: float, halo: float = 1.0) -> Optional[int]:
        best = None
        best_d = float("inf")
        for iid, item in self._items.items():
            cs = item["coords"]
            for j in range(0, len(cs), 2):
                dx = cs[j] - x
                dy = cs[j + 1] - y
                d = dx * dx + dy * dy
                if d < best_d:
                    best_d = d
                    best = iid
        return best

    def tag_bind(self, tag_or_id: Any, event: str, callback: Callable) -> None:
        ids = (
            self._find_ids(tag_or_id)
            if not isinstance(tag_or_id, str) or tag_or_id not in self._tags
            else self.find_withtag(tag_or_id)
        )
        if isinstance(tag_or_id, str) and tag_or_id in self._tags:
            if tag_or_id not in self._tag_bindings:
                self._tag_bindings[tag_or_id] = {}
            self._tag_bindings[tag_or_id][event] = callback
            return
        for iid in ids:
            if iid not in self._item_bindings:
                self._item_bindings[iid] = {}
            self._item_bindings[iid][event] = callback

    def _dispatch_event(self, item_id: int, event: str, data: Any) -> None:
        # item specific
        if item_id in self._item_bindings and event in self._item_bindings[item_id]:
            try:
                self._item_bindings[item_id][event](item_id, data)
            except Exception:
                pass
        # tags
        tags = self._items.get(item_id, {}).get("tags", set())
        for tag in tags:
            if tag in self._tag_bindings and event in self._tag_bindings[tag]:
                try:
                    self._tag_bindings[tag][event](item_id, data)
                except Exception:
                    pass

    def _invalidate_size(self):
        pass

    # small helpers
    def _find_ids(self, spec: Any) -> list[int]:
        if spec == "all":
            return list(self._items.keys())
        if isinstance(spec, int):
            return [spec] if spec in self._items else []
        if isinstance(spec, str):
            if spec.isdigit():
                try:
                    iid = int(spec)
                    if iid in self._items:
                        return [iid]
                except Exception:
                    pass
            if spec in self._tags:
                return list(self._tags[spec])
            return []
        if isinstance(spec, (list, tuple)):
            res: list[int] = []
            for s in spec:
                res += self._find_ids(s)
            return res
        return []


class Scale(Widget):
    """Scale / Slider widget for selecting a numeric value (tkinter Scale / ttk.Scale like).

    Supports:
    - from_, to, resolution (step)
    - orient: 'horizontal' or 'vertical'
    - variable (list holder for value)
    - command callback on change
    - length for main dimension
    - showvalue
    - grid and nesting
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        from_: float = 0,
        to: float = 100,
        resolution: float = 1,
        orient: str = "horizontal",
        variable: Optional[list] = None,
        command: Optional[Callable[[float], None]] = None,
        length: int = 100,
        showvalue: bool = True,
        font_size: int = 12,
    ) -> None:
        super().__init__(parent)
        self.from_ = from_
        self.to = to
        self.resolution = resolution
        self.orient = orient
        self.variable = variable or [from_]
        self.command = command
        self.length = length
        self.showvalue = showvalue
        self.font_size = font_size
        self._value = float(self.variable[0])
        self._min_height = 20 if orient == "horizontal" else length
        self._min_width = length if orient == "horizontal" else 20
        self._slider_size = 10

    def can_focus(self) -> bool:
        return not self._disabled

    def get(self) -> float:
        return self._value

    def set(self, val: float) -> None:
        val = max(self.from_, min(self.to, val))
        # snap to resolution
        if self.resolution > 0:
            val = round(val / self.resolution) * self.resolution
        self._value = val
        self.variable[0] = val
        if self.command:
            self.command(val)

    def _value_from_coord(self, coord: float) -> float:
        if self.orient == "horizontal":
            frac = max(0.0, min(1.0, (coord - self.x) / max(1, self.length)))
        else:
            frac = max(0.0, min(1.0, (coord - self.y) / max(1, self.length)))
        val = self.from_ + frac * (self.to - self.from_)
        if self.resolution > 0:
            val = round(val / self.resolution) * self.resolution
        return max(self.from_, min(self.to, val))

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self.contains(x, y) and not self._disabled:
            self._pressed = True
            coord = x if self.orient == "horizontal" else y
            val = self._value_from_coord(coord)
            if val != self._value:
                self.set(val)
            return True
        return False

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        if self._pressed and not self._disabled:
            coord = x if self.orient == "horizontal" else y
            val = self._value_from_coord(coord)
            if val != self._value:
                self.set(val)

    def on_mouse_release(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        self._pressed = False
        return False

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if self.orient == "horizontal":
            w = self.length + self._slider_size
            h = max(self._slider_size + 4, 20)
        else:
            w = max(self._slider_size + 4, 20)
            h = self.length + self._slider_size
        return w, h

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        frac = 0.0
        if self.to != self.from_:
            frac = (self._value - self.from_) / (self.to - self.from_)
        if self.orient == "horizontal":
            # trough
            trough_y = self.y + self.height / 2 - 2
            r.draw_rect(self.x, trough_y, self.length, 4, (0.3, 0.3, 0.3, 1.0))
            # slider
            sx = self.x + frac * (self.length - self._slider_size)
            r.draw_rect(
                sx,
                self.y + 2,
                self._slider_size,
                self.height - 4,
                (0.4, 0.6, 0.9, 1.0),
            )
            if self.showvalue:
                val_str = (
                    f"{self._value:.1f}"
                    if self.resolution < 1
                    else str(int(self._value))
                )
                tw, th = gui.measure_text(val_str, self.font_size) if gui else (20, 12)
                r.draw_text(
                    val_str,
                    self.x + self.length / 2 - tw / 2,
                    self.y + self.height + 2,
                    color=(0.9, 0.9, 0.9, 1.0),
                    font_size=self.font_size,
                )
        else:
            # vertical
            trough_x = self.x + self.width / 2 - 2
            r.draw_rect(trough_x, self.y, 4, self.length, (0.3, 0.3, 0.3, 1.0))
            sy = self.y + frac * (self.length - self._slider_size)
            r.draw_rect(
                self.x + 2,
                sy,
                self.width - 4,
                self._slider_size,
                (0.4, 0.6, 0.9, 1.0),
            )
            if self.showvalue:
                val_str = (
                    f"{self._value:.1f}"
                    if self.resolution < 1
                    else str(int(self._value))
                )
                tw, th = gui.measure_text(val_str, self.font_size) if gui else (20, 12)
                r.draw_text(
                    val_str,
                    self.x + self.width + 2,
                    self.y + self.length / 2 - th / 2,
                    color=(0.9, 0.9, 0.9, 1.0),
                    font_size=self.font_size,
                )


class Scrollbar(Widget):
    """Scrollbar widget (tkinter Scrollbar / ttk.Scrollbar like).

    - orient: 'vertical' or 'horizontal'
    - command: callback( 'moveto', fraction ) or ( 'scroll', n, 'units'/'pages' )
    - set(first, last): called by scrollable widget to update thumb
    - Used with Listbox, Text etc that implement yview / yview_moveto etc.
    - grid and nesting
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        orient: str = "vertical",
        command: Optional[Callable] = None,
        width: int = 16,
    ) -> None:
        super().__init__(parent)
        self.orient = orient
        self.command = command
        self.width = width
        self.first = 0.0
        self.last = 1.0
        self._min_size = 16

    def set(self, first: float, last: float) -> None:
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(self.first, min(1.0, float(last)))

    def _fraction_from_coord(self, coord: float) -> float:
        if self.orient == "vertical":
            size = self.height
            pos = coord - self.y
        else:
            size = self.width
            pos = coord - self.x
        if size <= 0:
            return 0.0
        frac = pos / size
        return max(0.0, min(1.0, frac))

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self.contains(x, y) and not self._disabled and self.command:
            self._pressed = True
            frac = self._fraction_from_coord(x if self.orient == "horizontal" else y)
            try:
                self.command("moveto", frac)
            except Exception:
                pass
            return True
        return False

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        if self._pressed and not self._disabled and self.command:
            frac = self._fraction_from_coord(x if self.orient == "horizontal" else y)
            try:
                self.command("moveto", frac)
            except Exception:
                pass

    def on_mouse_release(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        self._pressed = False
        return False

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if self.orient == "vertical":
            return self.width, max(self._min_size, 50)
        else:
            return max(self._min_size, 50), self.width

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        if self.orient == "vertical":
            r.draw_rect(self.x, self.y, self.width, self.height, (0.2, 0.2, 0.22, 1.0))
            r.draw_rect_border(
                self.x, self.y, self.width, self.height, 1.0, (0.3, 0.3, 0.35, 1.0)
            )
            # thumb
            thumb_size = max(10, int((self.last - self.first) * self.height))
            thumb_y = self.y + int(self.first * (self.height - thumb_size))
            r.draw_rect(
                self.x + 2,
                thumb_y,
                self.width - 4,
                thumb_size,
                (0.4, 0.5, 0.6, 1.0),
            )
        else:
            r.draw_rect(self.x, self.y, self.width, self.height, (0.2, 0.2, 0.22, 1.0))
            r.draw_rect_border(
                self.x, self.y, self.width, self.height, 1.0, (0.3, 0.3, 0.35, 1.0)
            )
            thumb_size = max(10, int((self.last - self.first) * self.width))
            thumb_x = self.x + int(self.first * (self.width - thumb_size))
            r.draw_rect(
                thumb_x,
                self.y + 2,
                thumb_size,
                self.height - 4,
                (0.4, 0.5, 0.6, 1.0),
            )


class Menu(Widget):
    """Menu widget supporting popup/context menus, cascades (submenus), separators,
    and basic menubar usage.

    Tkinter-inspired API:
        m = Menu(parent)
        m.add_command("Open", command=open_file)
        m.add_cascade("Recent", menu=recent_menu)
        m.add_separator()
        m.post(mouse_x, mouse_y)   # show as popup at absolute pos
        # or for menubutton integration: the Menubutton calls post for you.

    When posted (popup):
      - draws vertically at its posted rect
      - highlights on hover (via on_mouse_motion)
      - clicking command invokes + unposts chain
      - clicking cascade posts the submenu to the right
      - outside click (handled by GUIManager) or Esc dismisses

    Can also be placed via .grid() for custom menubar strips (draws horizontally).
    """

    def __init__(self, parent: Optional[Widget] = None, tearoff: bool = False) -> None:
        super().__init__(parent)
        self.tearoff = tearoff
        self.font_size = 14
        self._entries: list[dict[str, Any]] = []
        self._posted: bool = False
        self._active_index: Optional[int] = None
        # When posted these hold the absolute placement
        self._min_width = 120
        self._entry_height = 22
        self._sep_height = 6
        self._pad = 8

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if self._posted:
            return self._width or self._min_width, self._height or 10
        # menubar-ish horizontal preferred size
        w = 4
        h = self._entry_height
        for e in self._entries:
            if e["type"] == "separator":
                w += 8
                continue
            label_w = (len(e.get("label", "")) * (self.font_size * 0.6)) + 12
            w += label_w
        return max(w, self._min_width), h

    # --- Building the menu ---
    def add_command(
        self,
        label: str,
        command: Optional[Callable[[], None]] = None,
        accelerator: Optional[str] = None,
    ) -> None:
        self._entries.append(
            {
                "type": "command",
                "label": label,
                "command": command,
                "accelerator": accelerator,
            }
        )

    def add_cascade(
        self,
        label: str,
        menu: Optional["Menu"] = None,
        accelerator: Optional[str] = None,
    ) -> None:
        self._entries.append(
            {
                "type": "cascade",
                "label": label,
                "menu": menu,
                "accelerator": accelerator,
            }
        )

    def add_separator(self) -> None:
        self._entries.append({"type": "separator"})

    def delete(self, index: Any) -> None:
        """Delete by index or 'all'."""
        if index == "all":
            self._entries.clear()
            return
        try:
            del self._entries[int(index)]
        except Exception:
            pass

    def index(self, item: Any) -> int:
        """Return index for label or index specifier (basic)."""
        if isinstance(item, int):
            return item if 0 <= item < len(self._entries) else -1
        if isinstance(item, str):
            for i, e in enumerate(self._entries):
                if e.get("label") == item:
                    return i
        return -1

    def invoke(self, index: int) -> None:
        if 0 <= index < len(self._entries):
            entry = self._entries[index]
            if entry["type"] == "command":
                cmd = entry.get("command")
                if cmd:
                    try:
                        cmd()
                    except Exception:
                        pass
                self._unpost_chain()
            elif entry["type"] == "cascade":
                sub = entry.get("menu")
                if sub:
                    # post to the right of this menu entry
                    ex, ey = self._entry_screen_rect(index)
                    sub.post(ex + (self.width or 120) - 2, ey)
                    # register with gui if possible (if we can reach one)
                    # the post() path will have handled via caller usually

    def _unpost_chain(self) -> None:
        """Unpost this and any ancestor cascade menus."""
        self.unpost()
        # Best effort: if this menu was a submenu we don't have back pointer here.
        # GUIManager.dismiss_popups or individual unpost on parents will clean.

    def post(self, x: float, y: float, gui: Optional["GUIManager"] = None) -> None:
        """Show this menu as a popup at the given virtual coordinates."""
        self._compute_geometry()
        self.x = x
        self.y = y
        self.width = self._width
        self.height = self._height
        self._posted = True
        self._visible = True
        self._active_index = None
        if self.parent is not None and self not in self.parent.children:
            self.parent.children.append(self)
        # Move to end so it tends to be on top in normal tree walk
        if self.parent is not None and self in self.parent.children:
            self.parent.children.remove(self)
            self.parent.children.append(self)
        if gui is not None:
            # Use the manager's popup tracking for reliable top draw + outside dismiss
            try:
                gui.post_popup(self, x, y)
            except Exception:
                pass

    def unpost(self) -> None:
        self._posted = False
        self._visible = False
        self._active_index = None
        # close any open submenus
        for e in self._entries:
            if e.get("type") == "cascade":
                sub = e.get("menu")
                if sub and getattr(sub, "_posted", False):
                    sub.unpost()

    def _compute_geometry(self) -> None:
        """Calculate _width and _height based on current entries."""
        max_w = self._min_width
        h = 0
        for e in self._entries:
            if e["type"] == "separator":
                h += self._sep_height
                continue
            label = e.get("label", "")
            # approximate or use gui later; for now use char width
            w = (
                len(label) * (self.font_size * 0.6) + self._pad * 2 + 30
            )  # room for accel + cascade arrow
            if e.get("accelerator"):
                w += len(e["accelerator"]) * (self.font_size * 0.5) + 10
            max_w = max(max_w, w)
            h += self._entry_height
        self._width = max_w
        self._height = max(h, self._entry_height)

    def _entry_index_at(self, x: float, y: float) -> Optional[int]:
        """Return the entry index under local coords (relative to self.x/y)."""
        if not self._posted:
            return None
        rel_y = y - self.y
        y_acc = 0.0
        for i, e in enumerate(self._entries):
            eh = self._sep_height if e["type"] == "separator" else self._entry_height
            if y_acc <= rel_y < y_acc + eh:
                return i if e["type"] != "separator" else None
            y_acc += eh
        return None

    def _entry_screen_rect(self, idx: int) -> tuple[float, float]:
        """Return (left, top) screen position of the idx'th entry."""
        y_acc = self.y
        for i, e in enumerate(self._entries):
            eh = self._sep_height if e["type"] == "separator" else self._entry_height
            if i == idx:
                return (self.x, y_acc)
            y_acc += eh
        return (self.x, self.y)

    # --- Input ---
    def contains(self, x: float, y: float) -> bool:
        if self._posted:
            return self.x <= x < self.x + (self.width or 1) and self.y <= y < self.y + (
                self.height or 1
            )
        return super().contains(x, y)

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self._disabled or not self._visible:
            return False
        if not self.contains(x, y):
            return False
        idx = self._entry_index_at(x, y)
        if idx is None:
            # clicked on padding or separator
            return True
        entry = self._entries[idx]
        if entry["type"] == "command":
            cmd = entry.get("command")
            if cmd:
                try:
                    cmd()
                except Exception:
                    pass
            self._unpost_chain()
            return True
        elif entry["type"] == "cascade":
            sub = entry.get("menu")
            if sub:
                ex, ey = self._entry_screen_rect(idx)
                sub.post(ex + max(self.width or 100, 80) - 4, ey)
            return True
        return True

    def on_mouse_motion(
        self, x: float, y: float, *, gui: Optional["GUIManager"] = None
    ) -> None:
        if not self._posted or self._disabled:
            return
        self._active_index = self._entry_index_at(x, y)

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        if not self._posted:
            return False
        if key == pygame.K_ESCAPE:
            self._unpost_chain()
            return True
        if key == pygame.K_UP:
            self._move_active(-1)
            return True
        if key == pygame.K_DOWN:
            self._move_active(1)
            return True
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._active_index is not None:
                self.invoke(self._active_index)
            return True
        if key == pygame.K_LEFT:
            # could close current cascade - for now just unpost this level
            self.unpost()
            return True
        if key == pygame.K_RIGHT:
            if self._active_index is not None:
                e = self._entries[self._active_index]
                if e["type"] == "cascade" and e.get("menu"):
                    ex, ey = self._entry_screen_rect(self._active_index)
                    e["menu"].post(ex + (self.width or 100) - 4, ey)
            return True
        return False

    def _move_active(self, delta: int) -> None:
        n = len(self._entries)
        if n == 0:
            return
        start = (
            self._active_index
            if self._active_index is not None
            else (-1 if delta > 0 else n)
        )
        idx = start
        for _ in range(n + 1):
            idx = (idx + delta) % n
            if self._entries[idx]["type"] != "separator":
                self._active_index = idx
                return
        self._active_index = None

    # --- Drawing ---
    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        if not self._posted:
            # Basic menubar / horizontal strip style when gridded normally
            if self.width > 0 and self.height > 0:
                r.draw_rect(
                    self.x, self.y, self.width, self.height, (0.18, 0.18, 0.2, 1.0)
                )
            x_acc = self.x + 4
            for e in self._entries:
                if e["type"] == "separator":
                    x_acc += 8
                    continue
                label = e.get("label", "")
                tw, th = (
                    gui.measure_text(label, self.font_size)
                    if gui
                    else (len(label) * 7, self.font_size)
                )
                r.draw_text(
                    label,
                    x_acc,
                    self.y + 3,
                    color=(0.9, 0.9, 0.9, 1.0),
                    font_size=self.font_size,
                )
                x_acc += tw + 16
            return

        # Popup vertical menu
        if self.width <= 0 or self.height <= 0:
            self._compute_geometry()
            self.width = self._width
            self.height = self._height

        # background + border
        r.draw_rect(self.x, self.y, self.width, self.height, (0.15, 0.15, 0.17, 1.0))
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.3, 0.3, 0.35, 1.0)
        )

        y = self.y + 1
        for i, e in enumerate(self._entries):
            if e["type"] == "separator":
                r.draw_line(
                    self.x + 4,
                    y + self._sep_height / 2,
                    self.x + self.width - 4,
                    y + self._sep_height / 2,
                    1,
                    (0.35, 0.35, 0.38, 1.0),
                )
                y += self._sep_height
                continue

            eh = self._entry_height
            is_active = i == self._active_index
            if is_active:
                r.draw_rect(
                    self.x + 1, y, self.width - 2, eh - 1, (0.2, 0.35, 0.6, 0.6)
                )

            label = e.get("label", "")
            r.draw_text(
                label,
                self.x + self._pad,
                y + 3,
                color=(0.95, 0.95, 0.95, 1.0),
                font_size=self.font_size,
            )
            accel = e.get("accelerator")
            if accel:
                aw, _ = (
                    gui.measure_text(accel, self.font_size)
                    if gui
                    else (len(accel) * 5, 12)
                )
                r.draw_text(
                    accel,
                    self.x + self.width - self._pad - aw,
                    y + 3,
                    color=(0.7, 0.7, 0.75, 1.0),
                    font_size=self.font_size,
                )
            if e["type"] == "cascade":
                # small right arrow
                ax = self.x + self.width - self._pad - 8
                ay = y + eh / 2
                r.draw_line(ax - 4, ay - 3, ax, ay, 1, (0.8, 0.8, 0.85, 1))
                r.draw_line(ax, ay, ax - 4, ay + 3, 1, (0.8, 0.8, 0.85, 1))
            y += eh


class Menubutton(Widget):
    """A button-like widget that posts an associated Menu when clicked.

    Typically placed in a horizontal bar Frame for menubars.
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        text: str = "",
        menu: Optional[Menu] = None,
        font_size: int = 14,
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.menu = menu
        self.font_size = font_size
        self._min_width = 60
        self._min_height = 22

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if gui:
            tw, th = gui.measure_text(self.text, self.font_size)
        else:
            tw, th = len(self.text) * (self.font_size * 0.55), self.font_size * 1.3
        return max(tw + 28, self._min_width), max(th + 8, self._min_height)

    def on_click(self) -> None:
        if self.menu:
            # Post directly below the button
            mx = self.x
            my = self.y + self.height
            self.menu.post(mx, my)

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        # styling similar to button, plus small down indicator if has menu
        if self.disabled:
            bg = (0.25, 0.25, 0.25, 1.0)
            border = (0.35, 0.35, 0.35, 1.0)
            tc = (0.6, 0.6, 0.6, 1.0)
        elif self.pressed:
            bg = (0.12, 0.12, 0.14, 1.0)
            border = (0.1, 0.4, 0.8, 1.0)
            tc = (1.0, 1.0, 1.0, 1.0)
        elif self.hovered:
            bg = (0.32, 0.32, 0.35, 1.0)
            border = (0.2, 0.5, 0.9, 1.0)
            tc = (1.0, 1.0, 1.0, 1.0)
        else:
            bg = (0.22, 0.22, 0.25, 1.0)
            border = (0.18, 0.18, 0.22, 1.0)
            tc = (0.92, 0.92, 0.92, 1.0)

        r.draw_rect(self.x, self.y, self.width, self.height, bg)
        r.draw_rect_border(self.x, self.y, self.width, self.height, 1.0, border)

        tw, th = gui.measure_text(self.text, self.font_size)
        tx = self.x + 6
        ty = self.y + (self.height - th) / 2
        r.draw_text(self.text, tx, ty, color=tc, font_size=self.font_size)

        if self.menu:
            # small down triangle on the right
            ax = self.x + self.width - 10
            ay = self.y + self.height / 2
            r.draw_line(ax - 4, ay - 3, ax + 4, ay - 3, 1, tc)
            r.draw_line(ax - 4, ay - 3, ax, ay + 3, 1, tc)
            r.draw_line(ax + 4, ay - 3, ax, ay + 3, 1, tc)


class LabelFrame(Frame):
    """A container with a border and a text title label, similar to tkinter.LabelFrame / ttk.LabelFrame.

    Use exactly like Frame for children + grid:
        lf = LabelFrame(parent, text="Settings")
        lf.grid(row=0, column=0)
        child = Entry(lf, ...)
        child.grid(row=0, column=0)

    The label is drawn at the top; children are laid out below it in the framed content area.
    Supports grid_rowconfigure / grid_columnconfigure on the inner layout.
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        text: str = "",
        font_size: int = 14,
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.font_size = font_size

    def _get_label_size(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if not self.text:
            return 0.0, 0.0
        if gui is not None:
            return gui.measure_text(self.text, self.font_size)
        return len(self.text) * (self.font_size * 0.55), float(self.font_size) * 1.3

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        lw, lh = self._get_label_size(gui)
        if self.children:
            cw, ch = self._layout.get_preferred_size(self.children, gui)
        else:
            cw, ch = 0.0, 0.0
        side_pad = 8
        top_pad = (lh + 6) if self.text else 4
        w = max(lw + side_pad, cw + side_pad)
        h = top_pad + ch + side_pad
        if not self.text and not self.children:
            w, h = 100.0, 40.0
        return w, h

    def layout(
        self,
        children: list[Widget],
        avail_w: float,
        avail_h: float,
        gui: Optional["GUIManager"] = None,
    ) -> None:
        lw, lh = self._get_label_size(gui)
        label_space = (lh + 6) if self.text else 0
        inner_w = max(0.0, avail_w - 6)
        inner_h = max(0.0, avail_h - label_space - 4)

        # Register + layout content in the inner (reduced height) area
        self._layout.cells.clear()
        for child in children:
            if child.grid_options is not None:
                self._layout.add(child, child.grid_options)
        self._layout.layout(children, inner_w, inner_h, gui)

        # Translate children below the label + side padding (absolute)
        fx = self.x + 3
        fy = self.y + label_space + 2
        for child in children:
            if child.grid_options is not None:
                cx, cy, cw, ch = child.get_rect()
                child.set_rect(fx + cx, fy + cy, cw, ch)

        # Recurse into nested containers (same as Frame)
        for child in children:
            if hasattr(child, "layout") and child.grid_options is not None:
                child.layout(child.children, child.width, child.height, gui)

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        lw, lh = self._get_label_size(gui)

        if self.width > 0 and self.height > 0:
            # Full background + border (classic framed look)
            r.draw_rect(
                self.x, self.y, self.width, self.height, (0.18, 0.18, 0.2, 0.85)
            )
            r.draw_rect_border(
                self.x, self.y, self.width, self.height, 1.0, (0.3, 0.3, 0.35, 1.0)
            )

        if self.text:
            lx = self.x + 6
            ly = self.y + 2
            # Small patch behind the label so it interrupts the top border line
            tw = lw
            th = lh
            r.draw_rect(lx - 2, ly - 1, tw + 6, th + 3, (0.18, 0.18, 0.2, 0.95))
            r.draw_text(
                self.text,
                lx,
                ly,
                color=(0.88, 0.88, 0.92, 1.0),
                font_size=self.font_size,
            )

        # Children (already offset by layout() to sit inside the content area below label)
        for child in self.children:
            child.draw(gui)


class PanedWindow(Widget):
    """Resizable PanedWindow / split view container (tkinter PanedWindow / ttk.Panedwindow like).

    Supports two or more panes separated by draggable sashes.
    - orient: 'horizontal' (left/right panes) or 'vertical' (top/bottom)
    - .add(widget, minsize=..., weight=...)
    - Dragging sashes resizes adjacent panes live (via _sizes state + layout)
    - Works when placed via .grid() inside Frames; its direct children (panes) are managed internally
      (do not .grid() the panes for the split direction; they can have their own sub-layouts).
    - Sashes have visual grips; hit areas are forgiving for usability.

    Example:
        pw = PanedWindow(root, orient='horizontal')
        pw.grid(row=0, column=0, sticky='nsew')
        left = Frame(pw); pw.add(left, minsize=100)
        right = Frame(pw); pw.add(right)
        # later in loop: gui.layout(...); gui.handle_mouse(...)  --> drag updates sizes
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        orient: str = "horizontal",
        sashwidth: float = 5,
    ) -> None:
        super().__init__(parent)
        self.orient = orient if orient in ("horizontal", "vertical") else "horizontal"
        self.sashwidth = max(3, float(sashwidth))
        self._sizes: list[
            float
        ] = []  # major-axis sizes for each pane (updated by drag + layout)
        self._options: list[dict[str, Any]] = []  # parallel: {'minsize': , 'weight': }
        self._drag_sash: Optional[int] = None
        self._drag_start: float = 0.0
        self._drag_start_sizes: list[float] = []

    def add(
        self,
        widget: Widget,
        minsize: float = 10,
        weight: float = 1.0,
    ) -> None:
        """Add a pane widget. Reparents if necessary. Idempotent.

        Note: constructing Widget(parent=pw) auto-adds to .children; add() will sync
        _sizes/_options.
        """
        if widget not in self.children:
            if widget.parent is not None and widget.parent is not self:
                if widget in widget.parent.children:
                    widget.parent.children.remove(widget)
            widget.parent = self
            self.children.append(widget)
        # always sync lengths (ctor may have populated children) and (re)set options for this pane
        self._sync_lengths(len(self.children))
        try:
            idx = self.children.index(widget)
            self._options[idx]["minsize"] = float(minsize)
            self._options[idx]["weight"] = float(weight)
        except (ValueError, IndexError):
            pass

    def forget(self, widget: Widget) -> None:
        """Remove a pane (like Tk forget)."""
        if widget in self.children:
            try:
                idx = self.children.index(widget)
                self.children.remove(widget)
                if idx < len(self._sizes):
                    del self._sizes[idx]
                if idx < len(self._options):
                    del self._options[idx]
            except ValueError:
                pass

    def _get_minsize(self, idx: int) -> float:
        if 0 <= idx < len(self._options):
            return max(1.0, self._options[idx].get("minsize", 10.0))
        return 10.0

    def _sync_lengths(self, n: int) -> None:
        while len(self._sizes) < n:
            self._sizes.append(0.0)
        while len(self._options) < n:
            self._options.append({"minsize": 10.0, "weight": 1.0})
        if len(self._sizes) > n:
            self._sizes = self._sizes[:n]
            self._options = self._options[:n]

    def _init_sizes_if_needed(self, major_avail: float, n: int) -> None:
        if n <= 0:
            return
        self._sync_lengths(n)
        if sum(self._sizes[:n]) <= 0.1:
            sash_space = (n - 1) * self.sashwidth
            content = max(0.0, major_avail - sash_space)
            weights = [o.get("weight", 1.0) for o in self._options[:n]]
            tw = sum(weights) or float(n)
            for i in range(n):
                self._sizes[i] = content * weights[i] / tw

    def layout(
        self,
        children: list[Widget],
        avail_w: float,
        avail_h: float,
        gui: Optional["GUIManager"] = None,
    ) -> None:
        panes = children or self.children
        n = len(panes)
        if n == 0:
            return
        self._sync_lengths(n)

        is_h = self.orient == "horizontal"
        major_avail = avail_w if is_h else avail_h
        minor_avail = avail_h if is_h else avail_w

        self._init_sizes_if_needed(major_avail, n)

        # enforce mins + scale/clamp to fit (leaving room for sashes)
        for i in range(n):
            self._sizes[i] = max(self._get_minsize(i), self._sizes[i])
        total = sum(self._sizes[:n])
        sash_space = (n - 1) * self.sashwidth
        desired_pane_total = max(0.0, major_avail - sash_space)
        if (
            total > 0
            and desired_pane_total > 0
            and abs(total - desired_pane_total) > 0.5
        ):
            scale = desired_pane_total / total
            for i in range(n):
                self._sizes[i] *= scale
            for i in range(n):
                self._sizes[i] = max(self._get_minsize(i), self._sizes[i])

        # place panes (and leave sash gaps)
        pos = 0.0
        sw = self.sashwidth
        for i, child in enumerate(panes):
            sz = self._sizes[i] if i < len(self._sizes) else (major_avail / max(1, n))
            if is_h:
                child.set_rect(self.x + pos, self.y, sz, minor_avail)
            else:
                child.set_rect(self.x, self.y + pos, minor_avail, sz)
            pos += sz
            if i < n - 1:
                pos += sw

        # recurse (panes may be containers with their own layout)
        for child in panes:
            if hasattr(child, "layout"):
                child.layout(
                    getattr(child, "children", []),
                    child.width,
                    child.height,
                    gui,
                )

    def measure(self, gui: Optional["GUIManager"] = None) -> tuple[float, float]:
        if not self.children:
            return 250.0, 150.0
        n = len(self.children)
        self._sync_lengths(n)
        is_h = self.orient == "horizontal"
        major = 0.0
        minor = 0.0
        for i, child in enumerate(self.children):
            mw, mh = child.measure(gui) if hasattr(child, "measure") else (60.0, 40.0)
            m = mw if is_h else mh
            major += max(m, self._get_minsize(i))
            mn = mh if is_h else mw
            minor = max(minor, mn)
        major += (n - 1) * self.sashwidth
        return (major, minor) if is_h else (minor, major)

    # --- sash hit + drag ---
    def _sash_index_at(self, x: float, y: float) -> Optional[int]:
        if len(self.children) < 2:
            return None
        is_h = self.orient == "horizontal"
        rel = (x - self.x) if is_h else (y - self.y)
        cross = (y - self.y) if is_h else (x - self.x)
        minor_size = self.height if is_h else self.width
        if cross < 0 or cross > minor_size:
            return None
        cum = 0.0
        hit_extra = 3.0  # forgiving hit area
        for i in range(len(self.children) - 1):
            cum += self._sizes[i] if i < len(self._sizes) else 40.0
            sash_start = cum - hit_extra
            sash_end = cum + self.sashwidth + hit_extra
            if sash_start <= rel < sash_end:
                return i
            cum += self.sashwidth
        return None

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self._disabled or not self.contains(x, y):
            return False
        idx = self._sash_index_at(x, y)
        if idx is not None:
            self._drag_sash = idx
            self._drag_start = x if self.orient == "horizontal" else y
            self._drag_start_sizes = list(self._sizes)
            self._pressed = True
            return True
        return False

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        if self._drag_sash is None or self._disabled:
            return
        cur = x if self.orient == "horizontal" else y
        delta = cur - self._drag_start
        i = self._drag_sash
        if i is None or i >= len(self._sizes) - 1:
            return
        s0 = self._drag_start_sizes[i]
        s1 = self._drag_start_sizes[i + 1]
        min0 = self._get_minsize(i)
        min1 = self._get_minsize(i + 1)
        new0 = max(min0, min(s0 + delta, s0 + s1 - min1))
        self._sizes[i] = new0
        self._sizes[i + 1] = s0 + s1 - new0

    def on_mouse_release(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        self._drag_sash = None
        self._drag_start_sizes = []
        self._pressed = False
        return False

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        if len(self.children) < 2:
            # let children draw themselves (if any)
            for child in self.children:
                child.draw(gui)
            return

        is_h = self.orient == "horizontal"
        sw = self.sashwidth
        pos = 0.0
        for i in range(len(self.children) - 1):
            pos += self._sizes[i] if i < len(self._sizes) else 40.0
            if is_h:
                sx, sy = self.x + pos, self.y
                swd, sh = sw, self.height
            else:
                sx, sy = self.x, self.y + pos
                swd, sh = self.width, sw
            # sash bg
            r.draw_rect(sx, sy, swd, sh, (0.20, 0.20, 0.23, 1.0))
            r.draw_rect_border(sx, sy, swd, sh, 1.0, (0.28, 0.28, 0.32, 1.0))
            # simple grip (3 short lines or dots)
            if is_h:
                cx = sx + swd / 2
                cy = sy + sh / 2
                for off in (-4, 0, 4):
                    r.draw_line(
                        cx, cy + off, cx, cy + off + 3, 1.0, (0.55, 0.55, 0.6, 1.0)
                    )
            else:
                cx = sx + swd / 2
                cy = sy + sh / 2
                for off in (-4, 0, 4):
                    r.draw_line(
                        cx + off, cy, cx + off + 3, cy, 1.0, (0.55, 0.55, 0.6, 1.0)
                    )
            pos += sw

        # draw the pane contents (on top / in their rects)
        for child in self.children:
            child.draw(gui)


class Progressbar(Widget):
    """Progress indicator (tkinter/ttk.Progressbar like).

    Supports:
    - mode: 'determinate' (fills proportionally to value) or 'indeterminate' (animated segment)
    - orient: 'horizontal' or 'vertical'
    - maximum, value (clamped), optional variable=[val] for binding
    - length: preferred size for the long dimension (measure)
    - step(amount): advance value (det) or animation (indet)
    - start()/stop(): control indeterminate animation (advances phase each draw while running)

    When placed in a grid, it fills the allocated size for the bar (length affects only preferred/measure).
    Animation for indeterminate advances on draw calls when running (driven by game loop).
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        orient: str = "horizontal",
        mode: str = "determinate",
        maximum: float = 100.0,
        value: float = 0.0,
        length: float = 150.0,
        variable: Optional[list] = None,
    ) -> None:
        super().__init__(parent)
        self.orient = orient if orient in ("horizontal", "vertical") else "horizontal"
        self.mode = mode if mode in ("determinate", "indeterminate") else "determinate"
        self.maximum = max(1.0, float(maximum))
        self.length = max(20.0, float(length))
        self.variable = variable or [0.0]
        self._value = max(0.0, min(self.maximum, float(value)))
        self.variable[0] = self._value
        self._running = False
        self._tick = 0
        # visual thickness for the bar trough
        self._thickness = 12.0

    def can_focus(self) -> bool:
        return False  # not interactive

    def get(self) -> float:
        return self._value

    def set(self, value: float) -> None:
        self._value = max(0.0, min(self.maximum, float(value)))
        self.variable[0] = self._value

    def step(self, amount: float = 1.0) -> None:
        if self.mode == "determinate":
            self.set(self._value + amount)
        else:
            # advance animation phase for indeterminate
            self._tick += max(1, int(amount * 5))

    def start(self) -> None:
        """Begin indeterminate animation (advances on subsequent draw calls)."""
        if self.mode == "indeterminate":
            self._running = True

    def stop(self) -> None:
        """Stop indeterminate animation."""
        self._running = False

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        if self.orient == "horizontal":
            return self.length, self._thickness + 4
        else:
            return self._thickness + 4, self.length

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()

        # advance animation if running (indeterminate)
        if self.mode == "indeterminate" and self._running:
            self._tick += 1

        is_h = self.orient == "horizontal"
        trough_len = self.width if is_h else self.height
        trough_thick = self._thickness

        if is_h:
            tx = self.x
            ty = self.y + (self.height - trough_thick) / 2
            tw, th = trough_len, trough_thick
        else:
            tx = self.x + (self.width - trough_thick) / 2
            ty = self.y
            tw, th = trough_thick, trough_len

        # trough (background)
        r.draw_rect(tx, ty, tw, th, (0.25, 0.25, 0.28, 1.0))
        r.draw_rect_border(tx, ty, tw, th, 1.0, (0.35, 0.35, 0.38, 1.0))

        if self.mode == "determinate":
            frac = 0.0 if self.maximum == 0 else self._value / self.maximum
            frac = max(0.0, min(1.0, frac))
            if frac > 0:
                if is_h:
                    fw = tw * frac
                    r.draw_rect(tx, ty, fw, th, (0.35, 0.55, 0.85, 1.0))
                else:
                    fh = th * frac
                    r.draw_rect(tx, ty + (th - fh), tw, fh, (0.35, 0.55, 0.85, 1.0))
        else:
            # indeterminate: bouncing segment ~25% wide
            seg_frac = 0.25
            seg_len = trough_len * seg_frac
            # triangular wave position using tick (period ~ 40 draws)
            period = 40
            t = self._tick % (period * 2)
            if t > period:
                t = period * 2 - t
            offset_frac = t / period * (1.0 - seg_frac)
            offset = trough_len * offset_frac
            if is_h:
                r.draw_rect(tx + offset, ty, seg_len, th, (0.4, 0.65, 0.9, 1.0))
            else:
                r.draw_rect(tx, ty + offset, tw, seg_len, (0.4, 0.65, 0.9, 1.0))


class Notebook(Widget):
    """Tabbed notebook container (tkinter ttk.Notebook like).

    - .add(widget, text="Tab label")
    - .select(index) or .select(widget) to switch visible tab
    - Only the selected tab's widget is shown/drawn and laid out in the content area.
    - Tab bar at top with clickable labels.
    - Works nested in grid: place Notebook via .grid(), tab contents use their own layouts (e.g. Frames with .grid() inside).
    - Non-selected tabs have _visible=False to avoid input/draw interference.

    Example:
        nb = Notebook(root)
        nb.grid(row=0, column=0, sticky="nsew")
        tab1 = Frame(nb)
        nb.add(tab1, text="One")
        Label(tab1, text="Content 1").grid(row=0, column=0)
        tab2 = Frame(nb)
        nb.add(tab2, text="Two")
        ...
        nb.select(0)
    """

    def __init__(self, parent: Optional[Widget] = None, font_size: int = 14) -> None:
        super().__init__(parent)
        self.font_size = font_size
        self._tabs: list[dict[str, Any]] = []  # [{'widget': w, 'text': str}, ...]
        self._current: int = -1

    def add(self, widget: Widget, text: str = "") -> None:
        """Add a tab with associated content widget."""
        # reparent if needed (like PanedWindow/Menu)
        if widget not in self.children:
            if widget.parent is not None and widget.parent is not self:
                if widget in widget.parent.children:
                    widget.parent.children.remove(widget)
            widget.parent = self
            self.children.append(widget)

        # dedup in tabs list
        self._tabs = [t for t in self._tabs if t["widget"] is not widget]
        tab_text = text or f"Tab {len(self._tabs) + 1}"
        self._tabs.append({"widget": widget, "text": tab_text})

        if self._current < 0:
            self._current = len(self._tabs) - 1

        self._update_visibles()

    def forget(self, widget: Widget) -> None:
        """Remove tab."""
        self._tabs = [t for t in self._tabs if t["widget"] is not widget]
        if widget in self.children:
            self.children.remove(widget)
        if self._current >= len(self._tabs):
            self._current = len(self._tabs) - 1 if self._tabs else -1
        self._update_visibles()

    def select(self, index: int) -> None:
        """Select tab by index."""
        if 0 <= index < len(self._tabs):
            self._current = index
            self._update_visibles()

    def select_widget(self, widget: Widget) -> None:
        """Select tab containing the widget."""
        for i, t in enumerate(self._tabs):
            if t["widget"] is widget:
                self.select(i)
                return

    @property
    def current(self) -> int:
        return self._current

    def index(self, widget: Widget) -> int:
        for i, t in enumerate(self._tabs):
            if t["widget"] is widget:
                return i
        return -1

    def _update_visibles(self) -> None:
        for i, t in enumerate(self._tabs):
            t["widget"]._visible = i == self._current

    def _tab_height(self, gui: Optional["GUIManager"]) -> float:
        if gui:
            _, h = gui.measure_text("M", self.font_size)
            return h + 8
        return self.font_size + 10.0

    def layout(
        self,
        children: list[Widget],
        avail_w: float,
        avail_h: float,
        gui: Optional["GUIManager"] = None,
    ) -> None:
        if not self._tabs or self._current < 0:
            return
        tab_h = self._tab_height(gui)
        content_h = max(0.0, avail_h - tab_h)
        if self._current < len(self._tabs):
            child = self._tabs[self._current]["widget"]
            child.set_rect(self.x, self.y + tab_h, avail_w, content_h)
            if hasattr(child, "layout"):
                child.layout(
                    getattr(child, "children", []),
                    avail_w,
                    content_h,
                    gui,
                )

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        th = self._tab_height(gui)
        if not self._tabs:
            return 150.0, th + 80.0
        # min width from tabs
        min_w = 8.0
        for t in self._tabs:
            tw, _ = (
                gui.measure_text(t["text"], self.font_size)
                if gui
                else (len(t["text"]) * self.font_size * 0.55, self.font_size)
            )
            min_w += tw + 16
        # height: tab + reasonable content
        ch = 80.0
        if self._current >= 0 and self._current < len(self._tabs):
            w = self._tabs[self._current]["widget"]
            if hasattr(w, "measure"):
                _, ch = w.measure(gui)
        return max(min_w, 100.0), th + max(ch, 40.0)

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self._disabled or not self.contains(x, y):
            return False
        tab_h = self._tab_height(gui)  # approx ok for hit
        if y >= self.y + tab_h:
            return False  # in content, let child handle
        # hit in tab bar
        tx = self.x + 4
        for i, t in enumerate(self._tabs):
            txt = t["text"]
            tw, _ = (  # approx
                0,
                0,
            )  # we don't need gui here for rough, use char width
            tw = len(txt) * (self.font_size * 0.55) + 16
            if tx <= x < tx + tw:
                if i != self._current:
                    self.select(i)
                return True
            tx += tw + 2
        return True  # swallow clicks in tab strip

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        tab_h = self._tab_height(gui)
        # tab bar bg
        if self.width > 0 and tab_h > 0:
            r.draw_rect(self.x, self.y, self.width, tab_h, (0.18, 0.18, 0.2, 1.0))
        # draw tabs
        tx = self.x + 4
        for i, t in enumerate(self._tabs):
            txt = t["text"]
            tw, th = (
                gui.measure_text(txt, self.font_size)
                if gui
                else (len(txt) * self.font_size * 0.55, self.font_size)
            )
            tab_w = tw + 16
            is_cur = i == self._current
            bg = (0.28, 0.28, 0.32, 1.0) if is_cur else (0.15, 0.15, 0.18, 1.0)
            r.draw_rect(tx, self.y + 2, tab_w, tab_h - 4, bg)
            r.draw_rect_border(
                tx, self.y + 2, tab_w, tab_h - 4, 1.0, (0.3, 0.3, 0.35, 1.0)
            )
            # for current, cover bottom border to merge with content
            if is_cur:
                r.draw_rect(
                    tx + 1,
                    self.y + tab_h - 3,
                    tab_w - 2,
                    3,
                    (0.18, 0.18, 0.2, 1.0),
                )
            r.draw_text(
                txt,
                tx + 8,
                self.y + 4,
                color=(0.95, 0.95, 0.95, 1.0) if is_cur else (0.8, 0.8, 0.8, 1.0),
                font_size=self.font_size,
            )
            tx += tab_w + 2

        # draw content area bg + only current child
        if self._current >= 0 and self._current < len(self._tabs):
            cy = self.y + tab_h
            ch = max(0.0, self.height - tab_h)
            if ch > 0:
                r.draw_rect(self.x, cy, self.width, ch, (0.15, 0.15, 0.17, 0.9))
            self._tabs[self._current]["widget"].draw(gui)


class Treeview(Widget):
    """Hierarchical tree / multi-column list view (Tkinter ttk.Treeview inspired).

    Supports scene hierarchies, asset browsers, etc.
    - insert(parent, index, iid=None, text='', values=(), open=True)
    - delete(*iids), delete('all')
    - item(iid, option=None, **kw) for text/values/open
    - get_children(parent=''), selection, focus
    - heading(column, text=...), column(column, width=...)
    - expand/collapse via mouse on +/- or key left/right
    - single/browse or multiple select
    - yview for Scrollbar integration (vertical scroll of visible rows)
    - grid/nested compatible, uses Renderer + measure_text
    - keyboard (arrows, space) and mouse selection when focused
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        columns: tuple[str, ...] = (),
        height: int = 10,
        selectmode: str = "browse",
        font_size: int = 14,
    ) -> None:
        super().__init__(parent)
        self.columns: list[str] = list(columns)
        self.visible_lines = max(1, int(height))
        self.selectmode = selectmode
        self.font_size = font_size
        self._items: dict[str, dict] = {}
        self._parent: dict[str, str] = {}
        self._children: dict[str, list[str]] = {"": []}
        self._selected: list[str] = []
        self._focus: str = ""
        self._scroll: int = 0
        self._next_iid = 1
        self.yscrollcommand = None
        self._tree_col_width = 180.0
        self._col_widths: dict[str, float] = {c: 80.0 for c in self.columns}
        self._headings: dict[str, str] = {"#0": ""}
        for c in self.columns:
            self._headings[c] = c
        self._min_height = 20
        self._line_h = self.font_size * 1.3
        self._indent = 18.0
        # held key repeat for arrows
        self._next_repeat: dict[int, int] = {}
        self._repeat_delay = 300
        self._repeat_interval = 50

    def can_focus(self) -> bool:
        return not self._disabled

    def _gen_iid(self) -> str:
        while True:
            iid = f"I{self._next_iid}"
            if iid not in self._items:
                self._next_iid += 1
                return iid
            self._next_iid += 1

    def insert(
        self,
        parent: str = "",
        index: Any = "end",
        iid: Optional[str] = None,
        text: str = "",
        values: tuple[Any, ...] = (),
        open: bool = True,
        **kw: Any,
    ) -> str:
        if iid is None:
            iid = self._gen_iid()
        parent = parent or ""
        if parent not in self._children:
            self._children[parent] = []
        if iid in self._items:
            # replace
            pass
        self._items[iid] = {
            "text": text,
            "values": list(values),
            "open": bool(open),
            "tags": kw.get("tags", []),
        }
        self._parent[iid] = parent
        ch = self._children[parent]
        if index in (None, "end") or index < 0 or index > len(ch):
            ch.append(iid)
        else:
            ch.insert(int(index), iid)
        return iid

    def delete(self, *items: Any) -> None:
        if not items:
            return
        to_del = []

        def collect(iid: str):
            if iid in self._items:
                to_del.append(iid)
                for c in list(self._children.get(iid, [])):
                    collect(c)

        for it in items:
            if it == "all":
                self._items.clear()
                self._parent.clear()
                self._children = {"": []}
                self._selected.clear()
                self._focus = ""
                self._scroll = 0
                return
            collect(str(it))
        for iid in to_del:
            p = self._parent.get(iid, "")
            if p in self._children and iid in self._children[p]:
                self._children[p].remove(iid)
            self._items.pop(iid, None)
            self._parent.pop(iid, None)
            self._children.pop(iid, None)
            if iid in self._selected:
                self._selected.remove(iid)
        if self._focus in to_del:
            self._focus = ""
        if self._selected:
            self._selected = [s for s in self._selected if s not in to_del]
        self._clamp_scroll()

    def get_children(self, item: str = "") -> list[str]:
        return list(self._children.get(item or "", []))

    def item(self, iid: str, option: Optional[str] = None, **kw: Any) -> Any:
        iid = str(iid)
        if iid not in self._items:
            return None
        node = self._items[iid]
        if option is not None:
            if option == "text":
                return node.get("text", "")
            if option == "values":
                return node.get("values", [])
            if option == "open":
                return node.get("open", True)
            return node.get(option)
        if kw:
            for k, v in kw.items():
                if k == "text":
                    node["text"] = str(v)
                elif k == "values":
                    node["values"] = list(v)
                elif k == "open":
                    node["open"] = bool(v)
            return None
        return node.copy()

    def selection(self) -> list[str]:
        return list(self._selected)

    def selection_set(self, *items: str) -> None:
        self._selected = [str(i) for i in items if str(i) in self._items]

    def focus(self, iid: Optional[str] = None) -> Optional[str]:
        if iid is not None:
            iid = str(iid)
            if iid in self._items or iid == "":
                self._focus = iid
        return self._focus or (self._selected[0] if self._selected else "")

    def _get_visible(self) -> list[tuple[str, int]]:
        vis: list[tuple[str, int]] = []

        def rec(p: str, lev: int = 0):
            for iid in self._children.get(p, []):
                if iid in self._items:
                    vis.append((iid, lev))
                    if self._items[iid].get("open", True):
                        rec(iid, lev + 1)

        rec("")
        return vis

    def yview(self, *args: Any) -> Optional[tuple[float, float]]:
        vis = self._get_visible()
        total = max(1, len(vis))
        if args:
            if args[0] == "moveto":
                self._scroll = max(
                    0,
                    min(
                        int(float(args[1]) * total), max(0, total - self.visible_lines)
                    ),
                )
            elif args[0] == "scroll":
                n = int(args[1])
                if len(args) > 2 and args[2] == "pages":
                    n *= self.visible_lines
                self._scroll = max(
                    0, min(self._scroll + n, max(0, total - self.visible_lines))
                )
            self._clamp_scroll()
            if self.yscrollcommand:
                try:
                    self.yscrollcommand(*self.yview())
                except Exception:
                    pass
            return
        first = self._scroll / total
        last = min(1.0, (self._scroll + self.visible_lines) / total)
        if self.yscrollcommand:
            try:
                self.yscrollcommand(first, last)
            except Exception:
                pass
        return first, last

    def _clamp_scroll(self) -> None:
        vis = self._get_visible()
        total = len(vis)
        self._scroll = max(0, min(self._scroll, max(0, total - self.visible_lines)))

    def heading(self, column: str, text: Optional[str] = None, **kw: Any) -> Any:
        if text is not None:
            self._headings[column] = str(text)
        return self._headings.get(column, column)

    def column(self, column: str, width: Optional[float] = None, **kw: Any) -> Any:
        if width is not None:
            if column == "#0":
                self._tree_col_width = float(width)
            else:
                self._col_widths[column] = float(width)
        if column == "#0":
            return self._tree_col_width
        return self._col_widths.get(column, 80.0)

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        # rough width: tree col + cols
        w = self._tree_col_width
        for c in self.columns:
            w += self._col_widths.get(c, 80.0)
        h = self.visible_lines * self._line_h + 4
        return w + 8, max(h, self._min_height)

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if not self.contains(x, y) or self._disabled:
            return False
        self._pressed = True
        vis = self._get_visible()
        if not vis:
            return True
        line_h = self._line_h
        row = int((y - self.y) / line_h) + self._scroll
        if row < 0 or row >= len(vis):
            return True
        iid, lev = vis[row]
        relx = x - self.x
        indent = self._indent * lev
        # expander hit
        if self._children.get(iid):
            ex = 4 + indent
            if ex - 2 <= relx <= ex + 12:
                self._items[iid]["open"] = not self._items[iid].get("open", True)
                self._clamp_scroll()
                self.yview()
                return True
        # select row
        if self.selectmode in ("browse", "single"):
            self._selected = [iid]
        else:
            if iid in self._selected:
                self._selected.remove(iid)
            else:
                self._selected.append(iid)
        self._focus = iid
        # adjust scroll
        if row < self._scroll:
            self._scroll = row
        elif row >= self._scroll + self.visible_lines:
            self._scroll = row - self.visible_lines + 1
        self.yview()
        return True

    def on_key(self, key: int, char: str, mod: int = 0) -> bool:
        if self._disabled:
            return False
        vis = self._get_visible()
        if not vis:
            return False
        # find current pos in vis
        cur_iid = self._focus or (
            self._selected[0] if self._selected else (vis[0][0] if vis else "")
        )
        try:
            idx = next(i for i, (iid, _) in enumerate(vis) if iid == cur_iid)
        except StopIteration:
            idx = 0
        if key == pygame.K_UP:
            idx = max(0, idx - 1)
            new = vis[idx][0]
            self._focus = new
            if self.selectmode in ("browse", "single"):
                self._selected = [new]
            if idx < self._scroll:
                self._scroll = idx
            self.yview()
            return True
        if key == pygame.K_DOWN:
            idx = min(len(vis) - 1, idx + 1)
            new = vis[idx][0]
            self._focus = new
            if self.selectmode in ("browse", "single"):
                self._selected = [new]
            if idx >= self._scroll + self.visible_lines:
                self._scroll = idx - self.visible_lines + 1
            self.yview()
            return True
        if key == pygame.K_LEFT:
            if cur_iid and self._children.get(cur_iid):
                if self._items[cur_iid].get("open"):
                    self._items[cur_iid]["open"] = False
                    self.yview()
                    return True
            # go to parent
            p = self._parent.get(cur_iid, "")
            if p:
                self._focus = p
                if self.selectmode in ("browse", "single"):
                    self._selected = [p]
                # ensure parent visible in scroll
                self._clamp_scroll()
                self.yview()
                return True
        if key == pygame.K_RIGHT:
            if cur_iid and self._children.get(cur_iid):
                if not self._items[cur_iid].get("open"):
                    self._items[cur_iid]["open"] = True
                    self.yview()
                    return True
                else:
                    # go to first child
                    ch = self._children.get(cur_iid, [])
                    if ch:
                        new = ch[0]
                        self._focus = new
                        if self.selectmode in ("browse", "single"):
                            self._selected = [new]
                        self._clamp_scroll()
                        self.yview()
                        return True
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if cur_iid:
                if self.selectmode in ("browse", "single"):
                    self._selected = [cur_iid]
                else:
                    if cur_iid in self._selected:
                        self._selected.remove(cur_iid)
                    else:
                        self._selected.append(cur_iid)
            self.yview()
            return True
        self.yview()
        return False

    def on_key_state(self, pressed) -> bool:
        if self._disabled or not self._focused:
            return False
        now = pygame.time.get_ticks()
        mod = pygame.key.get_mods()
        repeatables = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT)
        for k in list(self._next_repeat.keys()):
            if not pressed[k]:
                self._next_repeat.pop(k, None)
        acted = False
        for k in repeatables:
            if not pressed[k]:
                continue
            nxt = self._next_repeat.get(k, 0)
            if nxt == 0:
                self._next_repeat[k] = now + self._repeat_delay
                if self.on_key(k, "", mod):
                    acted = True
                continue
            if now >= nxt:
                if self.on_key(k, "", mod):
                    self._next_repeat[k] = now + self._repeat_interval
                    acted = True
        return acted

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        # bg
        r.draw_rect(self.x, self.y, self.width, self.height, (0.1, 0.1, 0.12, 1.0))
        r.draw_rect_border(
            self.x, self.y, self.width, self.height, 1.0, (0.25, 0.25, 0.28, 1.0)
        )

        vis = self._get_visible()
        header_h = self._line_h if self.columns else 0.0
        if header_h > 0:
            r.draw_rect(self.x, self.y, self.width, header_h, (0.12, 0.12, 0.14, 1.0))
            # header texts
            hx = self.x + 4
            r.draw_text(
                "#0",
                hx,
                self.y + 1,
                color=(0.85, 0.85, 0.85, 1.0),
                font_size=self.font_size,
            )
            hx += self._tree_col_width
            for c in self.columns:
                r.draw_text(
                    self._headings.get(c, c),
                    hx,
                    self.y + 1,
                    color=(0.85, 0.85, 0.85, 1.0),
                    font_size=self.font_size,
                )
                hx += self._col_widths.get(c, 80.0)
            # line under header
            r.draw_line(
                self.x,
                self.y + header_h,
                self.x + self.width,
                self.y + header_h,
                1,
                (0.3, 0.3, 0.3, 1),
            )

        start_y = self.y + header_h
        line_h = self._line_h
        for i in range(self.visible_lines):
            vidx = self._scroll + i
            if vidx >= len(vis):
                break
            iid, lev = vis[vidx]
            node = self._items.get(iid, {})
            y = start_y + i * line_h
            indent = self._indent * lev
            x = self.x + 4 + indent
            # highlight
            if iid in self._selected:
                r.draw_rect(
                    self.x + 1, y, self.width - 2, line_h - 2, (0.2, 0.4, 0.7, 0.6)
                )
            # expander
            has_ch = bool(self._children.get(iid))
            if has_ch:
                sym = "-" if node.get("open", True) else "+"
                r.draw_text(
                    sym, x, y + 1, color=(0.9, 0.9, 0.9, 1.0), font_size=self.font_size
                )
                x += 14
            # main tree text
            r.draw_text(
                str(node.get("text", "")),
                x,
                y + 1,
                color=(0.9, 0.9, 0.9, 1.0),
                font_size=self.font_size,
            )
            # columns
            cx = self.x + 4 + self._tree_col_width
            vals = node.get("values", [])
            for j, c in enumerate(self.columns):
                v = str(vals[j]) if j < len(vals) else ""
                r.draw_text(
                    v,
                    cx,
                    y + 1,
                    color=(0.85, 0.85, 0.85, 1.0),
                    font_size=self.font_size,
                )
                cx += self._col_widths.get(c, 80.0)


class Separator(Widget):
    """Horizontal or vertical separator line.

    Tkinter Separator / ttk.Separator like.
    Used to visually divide sections in tools.
    """

    def __init__(
        self, parent: Optional[Widget] = None, orient: str = "horizontal"
    ) -> None:
        super().__init__(parent)
        self.orient = "vertical" if orient == "vertical" else "horizontal"

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        # Preferred: long in major direction, thin in minor. Actual size from grid/layout.
        if self.orient == "horizontal":
            return 100.0, 2.0
        else:
            return 2.0, 100.0

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        color = (0.35, 0.35, 0.38, 1.0)
        if self.orient == "horizontal":
            y = self.y + self.height / 2
            r.draw_line(self.x, y, self.x + self.width, y, 1.0, color)
        else:
            x = self.x + self.width / 2
            r.draw_line(x, self.y, x, self.y + self.height, 1.0, color)


class Sizegrip(Widget):
    """Resize grip (usually bottom-right corner handle for resizable panels/windows).

    Provides visual grip pattern and drag deltas via optional command.
    command: callable(dx, dy) called during drag with pixel deltas.
    Placed with grid sticky='se' etc.
    """

    def __init__(
        self,
        parent: Optional[Widget] = None,
        command: Optional[Callable[[float, float], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.command = command
        self._drag_start: Optional[tuple[float, float]] = None

    def measure(self, gui: Optional["GUIManager"]) -> tuple[float, float]:
        return 16.0, 16.0

    def draw(self, gui: "GUIManager") -> None:
        if not gui.get_renderer():
            return
        r = gui.get_renderer()
        # Small background square in bottom-right of allocated rect
        size = min(self.width, self.height, 16.0)
        bx = self.x + self.width - size
        by = self.y + self.height - size
        r.draw_rect(bx, by, size, size, (0.18, 0.18, 0.2, 0.8))
        # Grip pattern: 3 diagonal lines in corner (like Paned grip but diagonal)
        for i in range(3):
            off = i * 3 + 2
            r.draw_line(
                bx + size - 10 + off,
                by + size - 2,
                bx + size - 2,
                by + size - 10 + off,
                1.0,
                (0.55, 0.55, 0.6, 1.0),
            )

    def on_mouse_press(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        if self.contains(x, y) and not self._disabled:
            self._pressed = True
            self._drag_start = (x, y)
            return True
        return False

    def on_mouse_drag(
        self, x: float, y: float, button: int = 1, *, gui: Optional["GUIManager"] = None
    ) -> None:
        if not self._pressed or self._disabled or not self._drag_start:
            return
        sx, sy = self._drag_start
        dx = x - sx
        dy = y - sy
        if self.command:
            try:
                self.command(dx, dy)
            except Exception:
                pass
        self._drag_start = (x, y)

    def on_mouse_release(
        self, x: float, y: float, button: int, *, gui: Optional["GUIManager"] = None
    ) -> bool:
        self._pressed = False
        self._drag_start = None
        return False
