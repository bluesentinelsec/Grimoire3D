"""Console Demo — exercises the in-game developer console (issue #33).

Press  ~           to open / close the console.
Press  Tab         for command completion (forward).
Press  Shift+Tab   for command completion (reverse).
Press  Up/Down     to walk command history.
Press  Ctrl+R      for reverse history search.
Press  Cmd+V       (macOS) / Ctrl+V (Win/Linux) to paste from clipboard.
Press  Cmd+C       (macOS) / Ctrl+C (Win/Linux) to copy selection or input.
Click+drag         in the input row to select text.
Press  PgUp/PgDn   to scroll output.
Press  ESC         (in console) to close it.
Press  ESC         (outside console) to quit.

Registered demo commands (namespaced)
--------------------------------------
  gfx.color <name>     — change the background colour (red/green/blue/dark/default)
  gfx.gamma <val>      — get/set mock gamma
  gfx.brightness <val> — get/set mock brightness
  gfx.shadows [on|off] — toggle shadow rendering
  gfx.fog [on|off]     — toggle fog
  gfx.graphics         — print all current (mock) graphics settings
  demo.spam [n]        — dump n lines of output to fill the scroll buffer
  demo.crash           — trigger a handled error (tests error display)
  demo.enabled [on|off]— disable / re-enable the console itself at runtime
"""

from __future__ import annotations

import math
import os
import sys

import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from grimoire2d.presentation.window import GameWindow
from grimoire2d.gui.console import InGameConsole

# ---------------------------------------------------------------------------
# Demo state
# ---------------------------------------------------------------------------

VIRTUAL_W, VIRTUAL_H = 1920, 1080

_BG_COLORS: dict[str, tuple[int, int, int]] = {
    "default": (18,  20,  28),
    "dark":    (6,   6,   10),
    "red":     (45,  10,  10),
    "green":   (10,  35,  15),
    "blue":    (8,   16,  42),
}

_mock_settings = {
    "gamma":      2.2,
    "brightness": 1.0,
    "shadows":    True,
    "fog":        True,
    "specular":   True,
}


def _color_name_to_bar(name: str) -> tuple[int, int, int, int]:
    c = _BG_COLORS.get(name.lower())
    return (*c, 255) if c else None


def run() -> None:
    win = GameWindow(
        "Grimoire2D — Console Demo",
        virtual_width=VIRTUAL_W,
        virtual_height=VIRTUAL_H,
        target_fps=60,
        bar_color=(18, 20, 28, 255),
    )

    bg_color_name = "default"
    bg_rgb = _BG_COLORS[bg_color_name]
    anim_t = 0.0

    console = InGameConsole(VIRTUAL_W, VIRTUAL_H, enabled=True)

    # ------------------------------------------------------------------ #
    # Command handlers
    # ------------------------------------------------------------------ #

    def cmd_color(args: list[str]) -> str | None:
        nonlocal bg_color_name, bg_rgb
        if not args:
            names = ", ".join(_BG_COLORS)
            return f"Usage: color <name>   choices: {names}"
        name = args[0].lower()
        if name not in _BG_COLORS:
            return f"Unknown colour '{name}'.  Choices: {', '.join(_BG_COLORS)}"
        bg_color_name = name
        bg_rgb = _BG_COLORS[name]
        return f"Background set to '{name}'."

    def cmd_spam(args: list[str]) -> str | None:
        n = int(args[0]) if args else 30
        for i in range(n):
            console.print(f"  Spam line {i+1:03d} — the quick brown fox jumps over the lazy dog")
        return f"Printed {n} lines."

    def cmd_crash(args: list[str]) -> str | None:
        raise RuntimeError("This is a simulated error — the console caught it.")

    def cmd_graphics(_args: list[str]) -> str | None:
        lines = ["Current graphics settings:"]
        for k, v in _mock_settings.items():
            lines.append(f"  {k:<12} {v}")
        return "\n".join(lines)

    def cmd_gamma(args: list[str]) -> str | None:
        if not args:
            return f"gamma = {_mock_settings['gamma']}"
        try:
            v = float(args[0])
        except ValueError:
            return "Usage: gamma <float>"
        _mock_settings["gamma"] = round(v, 2)
        return f"gamma set to {_mock_settings['gamma']}"

    def cmd_brightness(args: list[str]) -> str | None:
        if not args:
            return f"brightness = {_mock_settings['brightness']}"
        try:
            v = float(args[0])
        except ValueError:
            return "Usage: brightness <float>"
        _mock_settings["brightness"] = round(v, 2)
        return f"brightness set to {_mock_settings['brightness']}"

    def cmd_shadows(args: list[str]) -> str | None:
        if args:
            _mock_settings["shadows"] = args[0].lower() in ("on", "true", "1", "yes")
        return f"shadows = {'on' if _mock_settings['shadows'] else 'off'}"

    def cmd_fog(args: list[str]) -> str | None:
        if args:
            _mock_settings["fog"] = args[0].lower() in ("on", "true", "1", "yes")
        return f"fog = {'on' if _mock_settings['fog'] else 'off'}"

    def cmd_enabled(args: list[str]) -> str | None:
        if not args:
            return f"console.enabled = {console.enabled}"
        console.enabled = args[0].lower() in ("on", "true", "1", "yes")
        return f"console.enabled set to {console.enabled}"

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    console.register_command("gfx.color",      cmd_color,      description="gfx.color <name> — set background colour (red/green/blue/dark/default)")
    console.register_command("gfx.gamma",      cmd_gamma,      description="gfx.gamma [val] — get/set output gamma")
    console.register_command("gfx.brightness", cmd_brightness, description="gfx.brightness [val] — get/set output brightness")
    console.register_command("gfx.shadows",    cmd_shadows,    description="gfx.shadows [on|off] — toggle shadow rendering")
    console.register_command("gfx.fog",        cmd_fog,        description="gfx.fog [on|off] — toggle fog")
    console.register_command("gfx.graphics",   cmd_graphics,   description="gfx.graphics — show all current (mock) graphics settings")
    console.register_command("demo.spam",      cmd_spam,       description="demo.spam [n] — flood output with n lines (default 30)")
    console.register_command("demo.crash",     cmd_crash,      description="demo.crash — trigger a handled runtime error")
    console.register_command("demo.enabled",   cmd_enabled,    description="demo.enabled [on|off] — disable/re-enable the console")

    # Greet
    console.print("Grimoire2D In-Game Console  —  type 'help' or 'std.help' for commands.", kind="info")
    console.print("Tab/Shift+Tab=complete  ↑↓=history  Ctrl+R=search  Cmd/Ctrl+C=copy  Cmd/Ctrl+V=paste", kind="info")
    console.print("Click+drag in the input row to select text.  PgUp/Dn=scroll", kind="info")

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #

    while win.is_open:
        for event in win.poll():
            if console.handle_event(event):
                continue
            if event.type == pygame.QUIT:
                win.close()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                win.close()

        dt = win.begin_frame()
        anim_t += dt
        console.update(dt)

        r  = win.renderer
        VW, VH = float(VIRTUAL_W), float(VIRTUAL_H)

        # Background
        br, bg, bb = bg_rgb
        r.draw_rect(0, 0, VW, VH, (br/255, bg/255, bb/255, 1.0))

        # Animated grid — subtle reference geometry so the overlay is obvious
        grid_alpha = 0.07
        grid_step  = 80
        for x in range(0, VIRTUAL_W, grid_step):
            r.draw_rect(x, 0, 1, VH, (0.3, 0.5, 0.8, grid_alpha))
        for y in range(0, VIRTUAL_H, grid_step):
            r.draw_rect(0, y, VW, 1, (0.3, 0.5, 0.8, grid_alpha))

        # Pulsing accent circle in the centre
        pulse  = 0.55 + 0.45 * math.sin(anim_t * 1.4)
        radius = 60 + 18 * math.sin(anim_t * 0.8)
        r.draw_circle(VW / 2, VH / 2, radius,
                      (0.20 * pulse, 0.60 * pulse, 1.00 * pulse, 0.18))
        r.draw_circle(VW / 2, VH / 2, radius * 0.55,
                      (0.40 * pulse, 0.80 * pulse, 1.00 * pulse, 0.22))

        # Instruction text (visible when console is closed)
        r.draw_text("Press  ~  to open the console  |  Tab/Shift+Tab=complete  |  Click+drag=select",
                    VW / 2 - 420, VH * 0.72, font_size=24,
                    color=(0.55, 0.70, 0.90, 0.80))
        r.draw_text(f"bg: {bg_color_name}   gamma: {_mock_settings['gamma']}   "
                    f"brightness: {_mock_settings['brightness']}   "
                    f"shadows: {'on' if _mock_settings['shadows'] else 'off'}   "
                    f"fog: {'on' if _mock_settings['fog'] else 'off'}",
                    VW / 2 - 400, VH * 0.78, font_size=22,
                    color=(0.40, 0.55, 0.75, 0.65))

        # Console overlay (drawn last so it's on top of everything)
        console.draw(r)

        win.end_frame()

    win.quit()


if __name__ == "__main__":
    run()
