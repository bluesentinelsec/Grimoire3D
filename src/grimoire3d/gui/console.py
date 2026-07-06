"""Quake-style in-game developer console.

Toggle with the ``~`` key.  Slides down from the top of the viewport with a
smooth animation, renders a subtle particle background, and provides a fully
featured readline-like input line (history, tab completion, reverse search,
clipboard integration, mouse selection).

Typical usage::

    console = InGameConsole(virtual_width=1920, virtual_height=1080)

    # Register commands (namespaced by convention)
    console.register_command("gfx.fog", lambda args: toggle_fog(args),
                             description="gfx.fog [on|off]")

    # Per-frame integration
    for event in win.poll():
        if console.handle_event(event):
            continue          # event was consumed by the console
        handle_game_event(event)

    dt = win.begin_frame()
    console.update(dt)

    # ... game drawing ...

    console.draw(win.renderer)
    win.end_frame()

Command namespacing
-------------------
Commands are registered under dot-separated namespaces by convention:

  std.*   — built-in shell-like commands (std.help, std.clear, std.echo, …)
  gfx.*   — graphics / render settings
  dbg.*   — debug / diagnostic toggles
  game.*  — game-logic commands

Mouse selection
---------------
Click and drag in the **input row** or **output area** to select text.
Cmd+C (macOS) / Ctrl+C (Windows/Linux) copies the selection.
Cmd+V (macOS) / Ctrl+V (Windows/Linux) pastes into the input row.

Release builds
--------------
Pass ``enabled=False`` to the constructor (or set ``console.enabled = False``)
to make the console completely inert — ``~`` is not intercepted,
``handle_event()`` always returns ``False``, and ``draw()`` is a no-op.
"""

from __future__ import annotations

import collections
import math
import platform
import random
import warnings
from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

import pygame
import pygame.scrap

if TYPE_CHECKING:
    from grimoire3d.presentation.renderer import Renderer

_IS_MAC     = platform.system() == "Darwin"
_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX   = platform.system() == "Linux"


# ---------------------------------------------------------------------------
# Clipboard helpers (cross-platform)
# ---------------------------------------------------------------------------

def _clipboard_set(text: str) -> None:
    """Write *text* to the system clipboard."""
    if _IS_MAC:
        import subprocess
        try:
            subprocess.run(["pbcopy"], input=text, text=True, timeout=1, check=True)
            return
        except Exception:
            pass
    if _IS_LINUX:
        import subprocess
        for cmd in (["xclip", "-selection", "clipboard"],
                    ["xsel", "--clipboard", "--input"],
                    ["wl-copy"]):
            try:
                subprocess.run(cmd, input=text, text=True, timeout=1, check=True)
                return
            except Exception:
                continue
    # pygame.scrap fallback (works on Windows; also catches macOS/Linux if
    # the subprocess helpers above failed)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pygame.scrap.put_text(text)
    except Exception:
        pass


def _clipboard_get() -> str:
    """Read a string from the system clipboard."""
    if _IS_MAC:
        import subprocess
        try:
            r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1)
            return r.stdout
        except Exception:
            pass
    if _IS_LINUX:
        import subprocess
        for cmd in (["xclip", "-selection", "clipboard", "-o"],
                    ["xsel", "--clipboard", "--output"],
                    ["wl-paste", "--no-newline"]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=1, check=True)
                return r.stdout
            except Exception:
                continue
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pygame.scrap.get_text() or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

@dataclass
class _Command:
    name:        str
    handler:     Callable[[list[str]], str | None]
    description: str = ""
    aliases:     list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Output line
# ---------------------------------------------------------------------------

@dataclass
class _Line:
    text: str
    kind: str = "output"   # "output" | "input" | "error" | "info"


# ---------------------------------------------------------------------------
# Particle
# ---------------------------------------------------------------------------

@dataclass
class _Particle:
    x:        float
    y:        float
    vx:       float
    vy:       float
    life:     float    # remaining lifetime in seconds
    max_life: float
    radius:   float
    hue:      float    # 0–1, cyan → purple


# ---------------------------------------------------------------------------
# InGameConsole
# ---------------------------------------------------------------------------

class InGameConsole:
    """Quake-style slide-down developer console."""

    # Visual constants
    _FONT_SIZE           = 20
    _LINE_H              = 24
    _PAD_X               = 14
    _PAD_Y               = 10
    _CURSOR_RATE         = 0.53
    _SLIDE_SPEED         = 10.0
    _MAX_PARTICLES       = 60
    _PARTICLE_SPAWN_RATE = 18

    # Colour palette (RGBA floats)
    _BG        = (0.04, 0.04, 0.07, 0.92)
    _BG_BORDER = (0.15, 0.55, 0.85, 0.70)
    _INPUT_BG  = (0.07, 0.07, 0.12, 1.00)
    _SEL_COLOR = (0.25, 0.55, 0.90, 0.40)
    _COL = {
        "output": (0.75, 0.85, 0.78, 1.0),
        "input":  (0.55, 0.80, 1.00, 1.0),
        "error":  (1.00, 0.38, 0.35, 1.0),
        "info":   (0.85, 0.75, 1.00, 1.0),
    }
    _CURSOR_COL  = (0.40, 0.85, 1.00, 1.0)
    _PROMPT      = "> "
    _SEARCH_PROMPT = "(reverse-i-search)`{query}': "

    def __init__(
        self,
        virtual_width:  int,
        virtual_height: int,
        *,
        height_frac:  float = 0.45,
        history_max:  int   = 200,
        enabled:      bool  = True,
    ) -> None:
        self.enabled  = enabled
        self._vw      = virtual_width
        self._vh      = virtual_height
        self._panel_h = int(virtual_height * height_frac)

        # Animation
        self._open      = False
        self._open_frac = 0.0

        # Input state
        self._input:    str   = ""
        self._cursor:   int   = 0
        self._cursor_t: float = 0.0

        # ---- Selection ----
        # sel_area: which area owns the active selection ("input" | "output" | None)
        self._sel_area:      str | None             = None
        # Input row selection (char indices into _input)
        self._sel_start:     int | None             = None
        self._sel_end:       int | None             = None
        # Output area selection ((abs_line_idx, char_idx) pairs)
        self._out_sel_start: tuple[int, int] | None = None
        self._out_sel_end:   tuple[int, int] | None = None
        # Mouse drag tracking
        self._dragging:      bool = False

        # Cached from draw() so handle_event() can do hit-testing
        self._renderer:      "Renderer | None" = None
        self._last_panel_y:  int               = -self._panel_h

        # History
        self._history:    collections.deque[str] = collections.deque(maxlen=history_max)
        self._hist_idx:   int = -1
        self._hist_draft: str = ""

        # Reverse search
        self._search_mode:  bool = False
        self._search_query: str  = ""
        self._search_idx:   int  = -1

        # Tab completion
        self._completions:    list[str] = []
        self._completion_idx: int       = -1

        # Output buffer
        self._lines:  list[_Line] = []
        self._scroll: int         = 0

        # Particles
        self._particles:   list[_Particle] = []
        self._spawn_accum: float = 0.0

        # Command registry
        self._commands: dict[str, _Command] = {}
        self._aliases:  dict[str, str]      = {}
        self._register_builtins()

    # ------------------------------------------------------------------
    # Public API — command registration
    # ------------------------------------------------------------------

    def register_command(
        self,
        name:        str,
        handler:     Callable[[list[str]], str | None],
        *,
        description: str            = "",
        aliases:     list[str] | None = None,
    ) -> None:
        """Register a console command (namespaced: ``gfx.fog``, ``std.echo``, …)."""
        cmd = _Command(name=name, handler=handler,
                       description=description, aliases=aliases or [])
        self._commands[name.lower()] = cmd
        for alias in (aliases or []):
            self._aliases[alias.lower()] = name.lower()

    def print(self, text: str, kind: str = "output") -> None:
        """Append one or more lines to the output buffer."""
        for line in str(text).splitlines() or [""]:
            self._lines.append(_Line(line, kind))
        self._scroll = 0

    def execute(self, command_str: str) -> None:
        """Parse and execute a command string programmatically."""
        self._run(command_str.strip())

    # ------------------------------------------------------------------
    # Public API — frame lifecycle
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a pygame event; returns True if the console consumed it."""
        if not self.enabled:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKQUOTE:
                self._toggle()
                return True
            if not self._open:
                return False
            return self._handle_keydown(event)

        if not self._open:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mousedown(event)
        if event.type == pygame.MOUSEMOTION:
            return self._handle_mousemotion(event)
        if event.type == pygame.MOUSEBUTTONUP:
            return self._handle_mouseup(event)

        if event.type in (pygame.KEYUP, pygame.TEXTINPUT):
            return True
        return False

    def update(self, dt: float) -> None:
        """Advance animation and particles.  Call once per frame."""
        if not self.enabled:
            return

        target = 1.0 if self._open else 0.0
        delta  = self._SLIDE_SPEED * dt
        self._open_frac = (min(target, self._open_frac + delta)
                           if self._open_frac < target
                           else max(target, self._open_frac - delta))

        if self._open_frac <= 0.0:
            return

        self._cursor_t += dt

        self._spawn_accum += self._PARTICLE_SPAWN_RATE * dt
        while self._spawn_accum >= 1.0 and len(self._particles) < self._MAX_PARTICLES:
            self._spawn_accum -= 1.0
            self._spawn_particle()

        keep: list[_Particle] = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            keep.append(p)
        self._particles = keep

    def draw(self, renderer: "Renderer") -> None:
        """Draw the console overlay.  Call after game drawing, before end_frame."""
        if not self.enabled or self._open_frac <= 0.0:
            return

        self._renderer = renderer

        frac    = _ease_out(self._open_frac)
        panel_y = -self._panel_h + int(self._panel_h * frac)
        self._last_panel_y = panel_y

        self._draw_background(renderer, panel_y)
        self._draw_particles(renderer, panel_y)
        self._draw_output(renderer, panel_y)
        self._draw_input(renderer, panel_y)
        self._draw_completions(renderer, panel_y)

    # ------------------------------------------------------------------
    # Built-in commands  (std.* namespace)
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        self.register_command(
            "std.help",    self._cmd_help,
            description="std.help [cmd] — list commands or show help for one",
            aliases=["help"])
        self.register_command(
            "std.clear",   self._cmd_clear,
            description="std.clear — clear the output buffer")
        self.register_command(
            "std.echo",    self._cmd_echo,
            description="std.echo <text> — print text to the console")
        self.register_command(
            "std.history", self._cmd_history,
            description="std.history — print command history")
        self.register_command(
            "std.quit",    self._cmd_quit,
            description="std.quit — signal the application to exit",
            aliases=["std.exit", "quit", "exit"])

    def _cmd_help(self, args: list[str]) -> str | None:
        if args:
            name = args[0].lower()
            name = self._aliases.get(name, name)
            cmd  = self._commands.get(name)
            if cmd:
                return cmd.description or f"{cmd.name}: no description"
            return f"Unknown command: {args[0]}"
        lines = sorted(
            f"  {c.name:<24} {c.description}" for c in self._commands.values()
        )
        return "Commands:\n" + "\n".join(lines)

    def _cmd_clear(self, _args: list[str]) -> str | None:
        self._lines.clear()
        self._scroll = 0
        return None

    def _cmd_echo(self, args: list[str]) -> str | None:
        return " ".join(args)

    def _cmd_history(self, _args: list[str]) -> str | None:
        if not self._history:
            return "(empty)"
        return "\n".join(f"  {i+1:3}  {cmd}" for i, cmd in enumerate(self._history))

    def _cmd_quit(self, _args: list[str]) -> str | None:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        return "Goodbye."

    # ------------------------------------------------------------------
    # Toggle
    # ------------------------------------------------------------------

    def _toggle(self) -> None:
        self._open = not self._open
        if self._open:
            self._cursor_t = 0.0
            self._cancel_search()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _phys_to_virt(self, mx: int, my: int) -> tuple[float, float]:
        """Physical window pixel → virtual (console) coordinate."""
        r = self._renderer
        if r is None:
            return float(mx), float(my)
        vp       = r.viewport
        ph       = r._phys[1]
        phys_top = ph - vp.viewport_y - vp.viewport_height
        return (mx - vp.viewport_x) / vp.scale, (my - phys_top) / vp.scale

    def _x_to_char(self, vx: float, text: str, base_x: float) -> int:
        """Map virtual x to nearest char boundary within *text* starting at *base_x*."""
        r = self._renderer
        if r is None:
            return 0
        prev_x = base_x
        for i in range(1, len(text) + 1):
            w, _   = r.measure_text(text[:i], font_size=self._FONT_SIZE)
            char_x = base_x + w
            if vx < (prev_x + char_x) / 2.0:
                return i - 1
            prev_x = char_x
        return len(text)

    def _input_base_x(self) -> float:
        r = self._renderer
        if r is None:
            return float(self._PAD_X) + len(self._PROMPT) * 8
        pw, _ = r.measure_text(self._PROMPT, font_size=self._FONT_SIZE)
        return float(self._PAD_X) + pw

    # ------------------------------------------------------------------
    # Hit-testing helpers
    # ------------------------------------------------------------------

    def _in_console(self, vy: float) -> bool:
        return self._last_panel_y <= vy <= self._last_panel_y + self._panel_h

    def _in_input_row(self, vy: float) -> bool:
        iy = self._last_panel_y + self._panel_h - self._LINE_H - self._PAD_Y
        return iy - 4 <= vy <= iy + self._LINE_H + 4

    def _in_output_area(self, vy: float) -> bool:
        top = self._last_panel_y + self._PAD_Y
        # Stop before the completions row and input row
        bot = self._last_panel_y + self._panel_h - self._LINE_H * 2 - self._PAD_Y - 4
        return top <= vy < bot

    def _vy_to_output_line(self, vy: float) -> int | None:
        """Return the absolute index into self._lines for the output row at vy, or None."""
        top   = self._last_panel_y + self._PAD_Y
        n     = self._visible_line_count()
        total = len(self._lines)
        end   = max(0, total - self._scroll)
        start = max(0, end - n)
        idx   = int((vy - top) / self._LINE_H)
        if 0 <= idx < (end - start):
            return start + idx
        return None

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _sel_range(self) -> tuple[int, int] | None:
        """Normalised (start, end) for the input-row selection, or None."""
        if self._sel_start is None or self._sel_end is None or self._sel_start == self._sel_end:
            return None
        a, b = self._sel_start, self._sel_end
        return (min(a, b), max(a, b))

    def _out_sel_range(self) -> tuple[int, int, int, int] | None:
        """Normalised (line_a, char_a, line_b, char_b) for the output selection, or None."""
        if self._out_sel_start is None or self._out_sel_end is None:
            return None
        s, e = self._out_sel_start, self._out_sel_end
        if s == e:
            return None
        if s > e:
            s, e = e, s
        return (s[0], s[1], e[0], e[1])

    def _clear_input_sel(self) -> None:
        self._sel_start = self._sel_end = None
        if self._sel_area == "input":
            self._sel_area = None

    def _clear_output_sel(self) -> None:
        self._out_sel_start = self._out_sel_end = None
        if self._sel_area == "output":
            self._sel_area = None

    def _delete_input_selection(self) -> None:
        sel = self._sel_range()
        if sel is None:
            return
        a, b = sel
        self._input  = self._input[:a] + self._input[b:]
        self._cursor = a
        self._clear_input_sel()
        self._reset_completions()
        self._cancel_search()

    # ------------------------------------------------------------------
    # Mouse handlers
    # ------------------------------------------------------------------

    def _handle_mousedown(self, event: pygame.event.Event) -> bool:
        if event.button != 1:
            return False
        vx, vy = self._phys_to_virt(event.pos[0], event.pos[1])
        if not self._in_console(vy):
            return False   # click outside panel — let game handle it

        if self._in_input_row(vy) and not self._search_mode:
            idx = self._x_to_char(vx, self._input, self._input_base_x())
            self._cursor    = idx
            self._sel_start = idx
            self._sel_end   = idx
            self._sel_area  = "input"
            self._clear_output_sel()
            self._dragging  = True
            self._cursor_t  = 0.0

        elif self._in_output_area(vy):
            li = self._vy_to_output_line(vy)
            if li is not None:
                ci = self._x_to_char(vx, self._lines[li].text, float(self._PAD_X))
                self._out_sel_start = (li, ci)
                self._out_sel_end   = (li, ci)
                self._sel_area      = "output"
                self._clear_input_sel()
                self._dragging = True

        return True   # swallow all clicks inside the panel

    def _handle_mousemotion(self, event: pygame.event.Event) -> bool:
        if not self._dragging:
            return False
        vx, vy = self._phys_to_virt(event.pos[0], event.pos[1])

        if self._sel_area == "input":
            idx           = self._x_to_char(vx, self._input, self._input_base_x())
            self._sel_end = idx
            self._cursor  = idx

        elif self._sel_area == "output":
            li = self._vy_to_output_line(vy)
            if li is None:
                # Clamp to top or bottom visible line
                top   = self._last_panel_y + self._PAD_Y
                n     = self._visible_line_count()
                total = len(self._lines)
                end   = max(0, total - self._scroll)
                start = max(0, end - n)
                li = start if vy < top else end - 1
                li = max(start, min(end - 1, li))
            if 0 <= li < len(self._lines):
                ci = self._x_to_char(vx, self._lines[li].text, float(self._PAD_X))
                self._out_sel_end = (li, ci)
        return True

    def _handle_mouseup(self, event: pygame.event.Event) -> bool:
        if event.button == 1:
            self._dragging = False
        return False

    # ------------------------------------------------------------------
    # Keyboard handler
    # ------------------------------------------------------------------

    def _handle_keydown(self, event: pygame.event.Event) -> bool:
        key   = event.key
        mod   = event.mod
        ctrl  = bool(mod & pygame.KMOD_CTRL)
        meta  = bool(mod & pygame.KMOD_META)   # Cmd on macOS
        shift = bool(mod & pygame.KMOD_SHIFT)

        # Clipboard modifier: Cmd on macOS, Ctrl on Windows/Linux
        clip_mod = meta if _IS_MAC else ctrl

        # --- Ctrl combos (readline) ---
        if ctrl:
            if key == pygame.K_r:
                self._start_or_advance_search()
                return True
            if key == pygame.K_a:
                self._cursor = 0
                self._clear_input_sel()
                return True
            if key == pygame.K_u:
                self._input  = self._input[self._cursor:]
                self._cursor = 0
                self._clear_input_sel(); self._cancel_search(); self._reset_completions()
                return True
            if key == pygame.K_k:
                self._input = self._input[:self._cursor]
                self._clear_input_sel(); self._cancel_search(); self._reset_completions()
                return True

        # --- Clipboard ---
        if clip_mod:
            if key == pygame.K_c:
                self._do_copy()
                return True
            if key == pygame.K_v:
                self._do_paste()
                return True

        # --- ESC ---
        if key == pygame.K_ESCAPE:
            if self._search_mode:
                self._cancel_search()
            else:
                self._open = False
            return True

        # --- Submit ---
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._submit()
            return True

        # --- History ---
        if key == pygame.K_UP:
            self._history_back()
            return True
        if key == pygame.K_DOWN:
            self._history_forward()
            return True

        # --- Cursor movement ---
        if key == pygame.K_LEFT:
            self._cursor = max(0, self._cursor - 1)
            self._clear_input_sel(); self._reset_completions()
            return True
        if key == pygame.K_RIGHT:
            self._cursor = min(len(self._input), self._cursor + 1)
            self._clear_input_sel(); self._reset_completions()
            return True
        if key == pygame.K_HOME:
            self._cursor = 0
            self._clear_input_sel()
            return True
        if key == pygame.K_END:
            self._cursor = len(self._input)
            self._clear_input_sel()
            return True

        # --- Tab completion (Shift+Tab reverses) ---
        if key == pygame.K_TAB:
            self._tab_complete(reverse=shift)
            return True

        # --- Scroll ---
        if key == pygame.K_PAGEUP:
            self._scroll_output(+1)
            return True
        if key == pygame.K_PAGEDOWN:
            self._scroll_output(-1)
            return True

        # --- Deletion ---
        if key == pygame.K_BACKSPACE:
            if self._search_mode:
                self._search_query = self._search_query[:-1]
                self._do_search(reverse=False)
            elif self._sel_range() is not None:
                self._delete_input_selection()
            elif self._cursor > 0:
                self._input  = self._input[:self._cursor-1] + self._input[self._cursor:]
                self._cursor -= 1
                self._reset_completions()
            return True

        if key == pygame.K_DELETE:
            if self._sel_range() is not None:
                self._delete_input_selection()
            elif self._cursor < len(self._input):
                self._input = self._input[:self._cursor] + self._input[self._cursor+1:]
                self._reset_completions()
            return True

        # --- Printable character ---
        char = event.unicode
        if char and char.isprintable():
            if self._search_mode:
                self._search_query += char
                self._do_search(reverse=False)
            else:
                sel = self._sel_range()
                if sel is not None:
                    a, b = sel
                    self._input  = self._input[:a] + char + self._input[b:]
                    self._cursor = a + 1
                    self._clear_input_sel()
                else:
                    self._input  = self._input[:self._cursor] + char + self._input[self._cursor:]
                    self._cursor += 1
                self._hist_idx = -1
                self._reset_completions()
            return True

        return True   # swallow all unhandled keys while open

    # ------------------------------------------------------------------
    # Clipboard operations
    # ------------------------------------------------------------------

    def _do_copy(self) -> None:
        """Copy selected text (output or input) to the system clipboard."""
        if self._sel_area == "output":
            sel = self._out_sel_range()
            if sel is None:
                return
            sl, sc, el, ec = sel
            parts: list[str] = []
            for i in range(sl, el + 1):
                text = self._lines[i].text
                if sl == el:
                    parts.append(text[sc:ec])
                elif i == sl:
                    parts.append(text[sc:])
                elif i == el:
                    parts.append(text[:ec])
                else:
                    parts.append(text)
            _clipboard_set("\n".join(parts))
        else:
            # Input area: copy selection or full line
            sel  = self._sel_range()
            text = self._input[sel[0]:sel[1]] if sel else self._input
            _clipboard_set(text)

    def _do_paste(self) -> None:
        """Paste from the system clipboard into the input row."""
        text = "".join(c for c in _clipboard_get() if c.isprintable())
        if not text:
            return
        sel = self._sel_range()
        if sel is not None:
            a, b = sel
            self._input  = self._input[:a] + text + self._input[b:]
            self._cursor = a + len(text)
            self._clear_input_sel()
        else:
            self._input  = self._input[:self._cursor] + text + self._input[self._cursor:]
            self._cursor += len(text)
        self._hist_idx = -1
        self._reset_completions()

    # ------------------------------------------------------------------
    # Input submission
    # ------------------------------------------------------------------

    def _submit(self) -> None:
        if self._search_mode:
            found = self._search_result()
            self._cancel_search()
            if found is not None:
                self._input  = found
                self._cursor = len(found)
            return

        cmd = self._input.strip()
        self._input  = ""
        self._cursor = 0
        self._hist_idx = -1
        self._clear_input_sel()
        self._reset_completions()

        if not cmd:
            return

        if not self._history or self._history[-1] != cmd:
            self._history.append(cmd)

        self.print(self._PROMPT + cmd, kind="input")
        self._run(cmd)

    def _run(self, cmd_str: str) -> None:
        parts = cmd_str.split()
        if not parts:
            return
        name = parts[0].lower()
        name = self._aliases.get(name, name)
        cmd  = self._commands.get(name)
        if cmd is None:
            self.print(f"Unknown command: {parts[0]!r}  (type 'help' for a list)", kind="error")
            return
        try:
            result = cmd.handler(parts[1:])
            if result is not None:
                self.print(str(result))
        except Exception as exc:
            self.print(f"Error: {exc}", kind="error")

    # ------------------------------------------------------------------
    # History navigation
    # ------------------------------------------------------------------

    def _history_back(self) -> None:
        self._cancel_search()
        self._clear_input_sel()
        if not self._history:
            return
        if self._hist_idx == -1:
            self._hist_draft = self._input
            self._hist_idx   = len(self._history) - 1
        elif self._hist_idx > 0:
            self._hist_idx -= 1
        self._input  = self._history[self._hist_idx]
        self._cursor = len(self._input)
        self._reset_completions()

    def _history_forward(self) -> None:
        self._clear_input_sel()
        if self._hist_idx == -1:
            return
        self._hist_idx += 1
        if self._hist_idx >= len(self._history):
            self._hist_idx = -1
            self._input    = self._hist_draft
        else:
            self._input = self._history[self._hist_idx]
        self._cursor = len(self._input)
        self._reset_completions()

    # ------------------------------------------------------------------
    # Reverse search
    # ------------------------------------------------------------------

    def _start_or_advance_search(self) -> None:
        if not self._search_mode:
            self._search_mode  = True
            self._search_query = ""
            self._search_idx   = len(self._history)
        self._do_search(reverse=True)

    def _do_search(self, *, reverse: bool) -> None:
        h     = list(self._history)
        start = self._search_idx - 1 if reverse else self._search_idx
        for i in range(start, -1, -1):
            if self._search_query.lower() in h[i].lower():
                self._search_idx = i
                return

    def _search_result(self) -> str | None:
        h = list(self._history)
        if 0 <= self._search_idx < len(h):
            return h[self._search_idx]
        return None

    def _cancel_search(self) -> None:
        self._search_mode  = False
        self._search_query = ""
        self._search_idx   = -1

    # ------------------------------------------------------------------
    # Tab completion
    # ------------------------------------------------------------------

    def _tab_complete(self, *, reverse: bool = False) -> None:
        token  = self._input[:self._cursor].split()
        prefix = token[-1].lower() if token else ""

        if self._completions and self._completion_idx >= 0:
            delta = -1 if reverse else +1
            self._completion_idx = (self._completion_idx + delta) % len(self._completions)
            chosen = self._completions[self._completion_idx]
        else:
            candidates = sorted(n for n in self._commands if n.startswith(prefix))
            if not candidates:
                return
            self._completions    = candidates
            self._completion_idx = len(candidates) - 1 if reverse else 0
            chosen               = candidates[self._completion_idx]

        before = self._input[:self._cursor]
        after  = self._input[self._cursor:]
        before = before[:before.rfind(" ")+1] if " " in before else ""
        self._input  = before + chosen + after
        self._cursor = len(before) + len(chosen)

    def _reset_completions(self) -> None:
        self._completions    = []
        self._completion_idx = -1

    # ------------------------------------------------------------------
    # Scroll
    # ------------------------------------------------------------------

    def _scroll_output(self, direction: int) -> None:
        max_scroll = max(0, len(self._lines) - self._visible_line_count())
        self._scroll = max(0, min(max_scroll, self._scroll + direction * 4))

    def _visible_line_count(self) -> int:
        usable = self._panel_h - self._PAD_Y * 2 - self._LINE_H * 2
        return max(1, usable // self._LINE_H)

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def _spawn_particle(self) -> None:
        p = _Particle(
            x        = random.uniform(0, self._vw),
            y        = self._panel_h - random.uniform(0, self._panel_h * 0.3),
            vx       = random.uniform(-12, 12),
            vy       = random.uniform(-28, -8),
            life     = random.uniform(1.2, 3.8),
            max_life = 0.0,
            radius   = random.uniform(1.0, 2.5),
            hue      = random.random(),
        )
        p.max_life = p.life
        self._particles.append(p)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_background(self, r: "Renderer", panel_y: int) -> None:
        r.draw_rect(0, panel_y, self._vw, self._panel_h, self._BG)
        r.draw_rect(0, panel_y + self._panel_h - 3, self._vw, 3, self._BG_BORDER)

    def _draw_particles(self, r: "Renderer", panel_y: int) -> None:
        for p in self._particles:
            t = p.life / p.max_life
            alpha = ((1.0 - t) / 0.15 if t > 0.85
                     else t / 0.40    if t < 0.40
                     else 1.0) * 0.55
            rc = 0.10 + p.hue * 0.40
            gc = 0.94 - p.hue * 0.60
            bc = min(1.0, 0.78 + p.hue * 0.38)
            r.draw_circle(p.x, panel_y + p.y, p.radius, (rc, gc, bc, alpha))

    def _draw_output(self, r: "Renderer", panel_y: int) -> None:
        n     = self._visible_line_count()
        total = len(self._lines)
        end   = max(0, total - self._scroll)
        start = max(0, end - n)

        out_sel = self._out_sel_range()   # (sl, sc, el, ec) or None

        y = panel_y + self._PAD_Y
        for rel, line in enumerate(self._lines[start:end]):
            abs_idx = start + rel
            col     = self._COL.get(line.kind, self._COL["output"])

            # Selection highlight
            if out_sel is not None:
                sl, sc, el, ec = out_sel
                if sl <= abs_idx <= el:
                    c_start = sc if abs_idx == sl else 0
                    c_end   = ec if abs_idx == el else len(line.text)
                    if c_start < c_end or (c_start == 0 and c_end == 0 and sl < abs_idx < el):
                        x0, _ = r.measure_text(line.text[:c_start], font_size=self._FONT_SIZE)
                        x1, _ = r.measure_text(line.text[:c_end],   font_size=self._FONT_SIZE)
                        # For fully-spanned middle lines select the full visible width
                        if sl < abs_idx < el:
                            x1, _ = r.measure_text(line.text, font_size=self._FONT_SIZE)
                        r.draw_rect(self._PAD_X + x0, y,
                                    max(6.0, x1 - x0), self._LINE_H - 2,
                                    self._SEL_COLOR)

            r.draw_text(line.text, self._PAD_X, y, font_size=self._FONT_SIZE, color=col)
            y += self._LINE_H

    def _draw_input(self, r: "Renderer", panel_y: int) -> None:
        input_y = panel_y + self._panel_h - self._LINE_H - self._PAD_Y

        r.draw_rect(0, input_y - 2, self._vw, self._LINE_H + 4, self._INPUT_BG)

        if self._search_mode:
            display_text = self._search_result() or ""
            prompt       = self._SEARCH_PROMPT.format(query=self._search_query)
        else:
            display_text = self._input
            prompt       = self._PROMPT

        # Input selection highlight
        sel = self._sel_range()
        if sel is not None and not self._search_mode:
            a, b  = sel
            pw, _ = r.measure_text(prompt, font_size=self._FONT_SIZE)
            x0, _ = r.measure_text(display_text[:a], font_size=self._FONT_SIZE)
            x1, _ = r.measure_text(display_text[:b], font_size=self._FONT_SIZE)
            r.draw_rect(self._PAD_X + pw + x0, input_y,
                        max(2.0, x1 - x0), self._LINE_H - 2, self._SEL_COLOR)

        r.draw_text(prompt + display_text, self._PAD_X, input_y,
                    font_size=self._FONT_SIZE, color=self._COL["input"])

        # Blinking cursor
        if int(self._cursor_t / self._CURSOR_RATE) % 2 == 0:
            ci  = self._cursor if not self._search_mode else len(display_text)
            pre = prompt + display_text[:ci]
            cx, _ = r.measure_text(pre, font_size=self._FONT_SIZE)
            r.draw_rect(self._PAD_X + cx, input_y, 2, self._LINE_H - 2, self._CURSOR_COL)

    def _draw_completions(self, r: "Renderer", panel_y: int) -> None:
        if len(self._completions) <= 1:
            return
        comp_y = panel_y + self._panel_h - self._LINE_H * 2 - self._PAD_Y - 4
        text = "  ".join(
            f"[{c}]" if i == self._completion_idx else c
            for i, c in enumerate(self._completions)
        )
        r.draw_text(text, self._PAD_X, comp_y,
                    font_size=self._FONT_SIZE - 2,
                    color=(0.55, 0.65, 0.55, 0.85))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3
