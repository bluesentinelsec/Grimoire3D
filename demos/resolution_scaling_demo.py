"""Resolution Scaling Demo

Design in 4K (3840×2160).  The engine figures out the rest.

How it works — the same pipeline used by Godot, Unity, and Unreal:

  1.  You define one virtual coordinate space: 3840×2160.
      Every position, size, and shape is expressed in those units.

  2.  At runtime the engine computes a scale factor:
          scale = min(physical_w / 3840, physical_h / 2160)
      The virtual canvas is drawn into a letterboxed region of the
      physical window at that scale.  Nothing more.

  3.  The GPU shades exactly as many pixels as the physical display has.
      On a 1728×1117 MacBook Pro: ~1.9 M pixels (scale ≈ 0.45).
      On a 3840×2160 4K display:  ~8.3 M pixels (scale = 1.0, pixel-perfect).
      On a 7680×4320 8K display:  scale ≈ 2.0, some softening — accepted
      trade-off, same as every AAA console title on a large TV.

  4.  No quality modes, no FBO tricks, no automatic adjustments.
      Resize the window freely — content stays in the same proportional
      layout and the letterbox adapts live.

Controls
--------
  ESC   Quit
  B     Toggle virtual canvas boundary
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pygame

from grimoire3d.presentation.window import GameWindow

# ---------------------------------------------------------------------------
# Fixed 4K virtual coordinate space — never changes
# ---------------------------------------------------------------------------
VW: float = 3840.0
VH: float = 2160.0


class _Anim:
    t: float = 0.0
    show_border: bool = True

    def tick(self, dt: float) -> None:
        self.t += dt


A = _Anim()


# ---------------------------------------------------------------------------
# Colour helper
# ---------------------------------------------------------------------------

def _hsv(h: float, s: float = 0.8, v: float = 1.0, a: float = 1.0) -> tuple:
    h6 = (h % 1.0) * 6.0
    i = int(h6)
    f = h6 - i
    p, q, t_ = v*(1-s), v*(1-f*s), v*(1-(1-f)*s)
    r, g, b = [(v,t_,p),(q,v,p),(p,v,t_),(p,q,v),(t_,p,v),(v,p,q)][i%6]
    return r, g, b, a


# ---------------------------------------------------------------------------
# Scene: animated primitives, all sizes/positions proportional to VW/VH
# ---------------------------------------------------------------------------

def draw_scene(r, t: float) -> None:
    cx, cy = VW * 0.5, VH * 0.5
    mn = min(VW, VH)

    # Background
    r.draw_rect_gradient(
        0, 0, VW, VH,
        color_top=(0.04, 0.04, 0.10, 1.0),
        color_bottom=(0.09, 0.06, 0.15, 1.0),
    )

    # Reference grid
    gc = (0.18, 0.18, 0.28, 0.22)
    for i in range(1, 16):
        r.draw_line(VW*i/16, 0, VW*i/16, VH, 2.0, gc)
    for i in range(1, 9):
        r.draw_line(0, VH*i/9, VW, VH*i/9, 2.0, gc)

    # Radial glow
    r.draw_circle_gradient(
        cx, cy, mn*0.38,
        color_center=(0.14, 0.10, 0.30, 0.55),
        color_edge=(0.04, 0.04, 0.12, 0.0),
        segments=64,
    )

    # Orbiting circles
    orb_r = mn * 0.22
    cr = mn * 0.028
    for i in range(12):
        angle = t*0.7 + 2*math.pi*i/12
        ox = cx + math.cos(angle)*orb_r
        oy = cy + math.sin(angle)*orb_r
        r.draw_drop_shadow(ox-cr, oy-cr, cr*2, cr*2,
                           ox=cr*0.3, oy=cr*0.3, blur=cr*0.9,
                           color=(0,0,0,0.4))
        r.draw_circle(ox, oy, cr, _hsv(i/12))

    # Rotating hexagon
    pa = t * 0.55
    pr = mn * 0.12
    pts = [(cx + math.cos(pa + 2*math.pi*i/6)*pr,
            cy + math.sin(pa + 2*math.pi*i/6)*pr) for i in range(6)]
    r.draw_polygon(pts, (0.38, 0.72, 1.0, 0.85))
    r.draw_polyline(pts, mn*0.004, (1.0, 1.0, 1.0, 0.5), closed=True)

    # Pulsing ring
    pulse = math.sin(t*1.9)
    ro = mn*(0.17 + pulse*0.012)
    r.draw_ring(cx, cy, ro, ro*0.78, (0.85, 0.45, 1.0, 0.55))

    # Arc
    r.draw_arc(cx, cy, mn*0.205, 0.0, (t*0.85) % (2*math.pi),
               thickness=mn*0.007, color=(0.3, 1.0, 0.7, 0.9))

    # Animated cubic Bézier
    bx0, by0 = VW*0.04, VH*0.76
    bx1, by1 = VW*0.96, VH*0.76
    bcx0 = VW*(0.20 + 0.15*math.sin(t*0.75))
    bcy0 = VH*(0.28 + 0.24*math.cos(t*0.60))
    bcx1 = VW*(0.72 + 0.14*math.cos(t*0.68))
    bcy1 = VH*(0.48 + 0.20*math.sin(t*0.88))
    r.draw_bezier_cubic(bx0, by0, bcx0, bcy0, bcx1, bcy1, bx1, by1,
                        thickness=mn*0.005, color=(1.0, 0.6, 0.2, 0.85),
                        segments=48)

    # Corner accents
    pad = VW*0.018
    rw, rh = VW*0.10, VH*0.055
    rad = rh*0.38
    for (rx, ry), col in zip(
        [(pad,pad),(VW-pad-rw,pad),(pad,VH-pad-rh),(VW-pad-rw,VH-pad-rh)],
        [(0.3,0.65,1.0,0.75),(1.0,0.50,0.28,0.75),
         (0.4,0.90,0.5,0.75),(1.0,0.80,0.2,0.75)],
    ):
        r.draw_drop_shadow(rx, ry, rw, rh, blur=rad*1.5, color=(0,0,0,0.35))
        r.draw_rect_rounded(rx, ry, rw, rh, rad, col)
        r.draw_rect_rounded_border(rx, ry, rw, rh, rad, max(2,VW*0.0008),
                                   (1,1,1,0.28))

    # Dashed crosshairs
    dc = (0.4, 0.4, 0.65, 0.3)
    step = VW*0.012
    r.draw_dashed_line(cx, 0, cx, VH, 1.5, dc, dash=step, gap=step)
    r.draw_dashed_line(0, cy, VW, cy, 1.5, dc, dash=step, gap=step)


# ---------------------------------------------------------------------------
# Widget strip — proportional renderer primitives (no GUIManager sizing issues)
# ---------------------------------------------------------------------------

def draw_widget_strip(r, t: float) -> None:
    strip_y = VH * 0.875
    strip_h = VH * 0.095
    fs = max(18, int(VH * 0.020))

    r.draw_rect_gradient(
        0, strip_y - VH*0.02, VW, strip_h + VH*0.04,
        color_top=(0.06, 0.06, 0.12, 0.0),
        color_bottom=(0.06, 0.06, 0.12, 0.96),
    )
    r.draw_line(0, strip_y, VW, strip_y, 1.5, (0.35, 0.35, 0.55, 0.45))

    btn_w = VW*0.075
    btn_h = strip_h*0.56
    btn_r = btn_h*0.32
    btn_y = strip_y + (strip_h - btn_h)*0.45
    gap = VW*0.012
    x = gap*2

    for label, col in [
        ("New",      (0.30,0.60,1.00,0.9)),
        ("Open",     (0.28,0.70,0.42,0.9)),
        ("Save",     (0.85,0.50,0.20,0.9)),
        ("Export",   (0.70,0.28,0.85,0.9)),
        ("Settings", (0.38,0.68,0.80,0.9)),
        ("Help",     (0.50,0.50,0.60,0.9)),
    ]:
        r.draw_drop_shadow(x, btn_y, btn_w, btn_h, blur=btn_h*0.22,
                           color=(0,0,0,0.28))
        r.draw_rect_rounded(x, btn_y, btn_w, btn_h, btn_r, col)
        r.draw_rect_rounded_border(x, btn_y, btn_w, btn_h, btn_r,
                                   max(2,VW*0.001), (1,1,1,0.25))
        r.draw_text_centered(label, x+btn_w/2, btn_y+btn_h/2,
                             color=(1,1,1,0.95), font_size=fs)
        x += btn_w + gap

    x += gap
    r.draw_line(x, btn_y, x, btn_y+btn_h, max(2,VW*0.001), (0.5,0.5,0.7,0.35))
    x += gap*2

    # Progress bar
    pb_w = VW*0.18
    pb_h = btn_h*0.30
    pb_y = btn_y + (btn_h - pb_h)*0.35
    pb_val = math.sin(t*0.45)*0.5 + 0.5
    r.draw_text("Export Progress", x, pb_y - pb_h*2.5,
                color=(0.65,0.75,0.90,0.85), font_size=int(fs*0.82))
    r.draw_rect_rounded(x, pb_y, pb_w, pb_h, pb_h*0.5, (0.14,0.14,0.24,0.9))
    if pb_val > 0.01:
        r.draw_rect_rounded(x, pb_y, pb_w*pb_val, pb_h, pb_h*0.5,
                            (0.38,0.82,0.52,1.0))
    r.draw_text(f"{pb_val*100:.0f}%", x+pb_w+gap, pb_y,
                color=(0.7,0.9,0.7,0.9), font_size=int(fs*0.82))
    x += pb_w + gap*3

    # Slider
    sl_w = VW*0.14
    sl_y = btn_y + btn_h*0.5
    sl_t = btn_h*0.09
    sl_val = math.sin(t*0.65 + 1.2)*0.5 + 0.5
    thumb_r = btn_h*0.24
    r.draw_text("Opacity", x, sl_y - btn_h*0.56,
                color=(0.65,0.75,0.90,0.85), font_size=int(fs*0.82))
    r.draw_capsule(x, sl_y - sl_t/2, sl_w, sl_t, (0.22,0.22,0.34,1.0))
    r.draw_capsule(x, sl_y - sl_t/2, sl_w*sl_val, sl_t, (0.48,0.70,1.0,1.0))
    r.draw_circle(x + sl_w*sl_val, sl_y, thumb_r, (0.85,0.93,1.0,1.0))
    r.draw_text(f"{sl_val*100:.0f}%",
                x + sl_w*sl_val - btn_w*0.18, sl_y - thumb_r - fs*1.2,
                color=(0.8,0.9,1.0,0.95), font_size=int(fs*0.80))
    x += sl_w + gap*3

    # Checkboxes
    cb = btn_h*0.48
    for label, checked in [("Grid", True), ("Snap", True), ("Alpha", False)]:
        cy2 = btn_y + (btn_h - cb)/2
        r.draw_rect_rounded(x, cy2, cb, cb, cb*0.22, (0.18,0.18,0.28,0.95))
        r.draw_rect_rounded_border(x, cy2, cb, cb, cb*0.22,
                                   max(1,VW*0.0005), (0.55,0.55,0.75,0.65))
        if checked:
            inn = cb*0.58
            off = (cb - inn)/2
            r.draw_rect_rounded(x+off, cy2+off, inn, inn, inn*0.25,
                                (0.4,0.75,1.0,1.0))
        r.draw_text(label, x+cb+gap, btn_y+(btn_h-fs)*0.52,
                    color=(0.75,0.80,0.90,0.90), font_size=fs)
        x += cb + gap + r.measure_text(label, font_size=fs)[0] + gap*2


# ---------------------------------------------------------------------------
# Info panel — top-right, proportional to VW/VH
# ---------------------------------------------------------------------------

def draw_info_panel(r, fps: float, scale: float,
                    phys_w: int, phys_h: int) -> None:
    pad = VW*0.018
    pw  = VW*0.255
    ph  = VH*0.185
    px  = VW - pw - pad
    py  = pad

    r.draw_drop_shadow(px, py, pw, ph, blur=ph*0.14, color=(0,0,0,0.45))
    r.draw_rect_rounded(px, py, pw, ph, ph*0.09, (0.06,0.06,0.14,0.92))
    r.draw_rect_rounded_border(px, py, pw, ph, ph*0.09,
                                max(2,VW*0.0008), (0.45,0.45,0.80,0.55))

    lh  = ph * 0.185
    fs  = max(16, int(VH*0.020))
    lx  = px + pw*0.06
    ty  = py + ph*0.10

    r.draw_text("Renderer", lx, ty,
                color=(0.75,0.85,1.0,1.0), font_size=int(fs*1.18))
    ty += lh*1.25

    for label, value in [
        ("Virtual",  f"{int(VW)}×{int(VH)}  (4K design space)"),
        ("Physical", f"{phys_w}×{phys_h}"),
        ("Scale",    f"{scale:.4f}×"),
        ("FPS",      f"{fps:.0f}"),
    ]:
        r.draw_text(f"{label}:", lx, ty,
                    color=(0.50,0.55,0.72,0.85), font_size=fs)
        r.draw_text(value, lx+pw*0.34, ty,
                    color=(0.88,0.92,1.00,1.00), font_size=fs)
        ty += lh

    ty += lh*0.15
    r.draw_line(lx, ty, px+pw*0.94, ty, max(1,VW*0.0004), (0.35,0.35,0.55,0.4))
    ty += lh*0.35

    r.draw_text("[B] toggle border    [ESC] quit",
                lx, ty, color=(0.42,0.42,0.62,0.80),
                font_size=max(13, int(VH*0.016)))


# ---------------------------------------------------------------------------
# Coverage bar — proves GPU is rendering at native res, not 4K
# ---------------------------------------------------------------------------

def draw_coverage_bar(r, scale: float) -> None:
    bx, by = VW*0.018, VH*0.015
    bw, bh = VW*0.25, VH*0.008
    fs = max(13, int(VH*0.016))

    r.draw_rect_rounded(bx, by, bw, bh, bh*0.5, (0.15,0.15,0.25,0.8))
    r.draw_rect_rounded(bx, by, bw*min(scale,1.0), bh, bh*0.5,
                        (0.4,0.80,0.5,1.0))
    r.draw_text(
        f"Pixel coverage: {scale*100:.1f}%  "
        f"({'native 4K' if scale >= 0.999 else 'scaled — GPU renders at physical res only'})",
        bx, by + bh + VH*0.008,
        color=(0.55,0.75,0.60,0.85), font_size=fs,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Grimoire3D — 4K Resolution Scaling Demo")
    print(f"Virtual design space: {int(VW)}×{int(VH)}")
    print("GPU always renders at the physical display resolution.")
    print("Resize the window freely — B to toggle border, ESC to quit.")

    win = GameWindow(
        "Grimoire3D — 4K Resolution Scaling Demo",
        virtual_width=int(VW),
        virtual_height=int(VH),
        target_fps=60,
    )
    r = win.renderer

    while win.is_open:
        for event in win.poll():
            if event.type == pygame.QUIT:
                win.close()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    win.close()
                elif event.key == pygame.K_b:
                    A.show_border = not A.show_border

        dt = win.begin_frame()
        A.tick(dt)

        vp    = win.viewport
        scale = vp.scale
        fps   = win.fps

        draw_scene(r, A.t)
        draw_widget_strip(r, A.t)
        draw_info_panel(r, fps, scale, vp.physical_width, vp.physical_height)
        draw_coverage_bar(r, scale)

        if A.show_border:
            r.draw_virtual_border(thickness=max(4.0, min(VW,VH)*0.003))

        win.end_frame()

    win.quit()


if __name__ == "__main__":
    main()
