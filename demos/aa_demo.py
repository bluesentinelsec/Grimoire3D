"""Anti-Aliasing Demo — AA Mode Comparison

A scene designed with high-contrast edges, thin geometry, and diagonal
lines to make aliasing artifacts clearly visible.  Cycle through AA
modes in real-time to compare quality.

Scene: an outdoor-style area with a grid ground plane, rotated boxes at
various angles, and thin cylindrical poles.

Controls:
  Mouse               look (click to capture)
  WASD                strafe / walk
  Q / E               fly up / down
  1                   cycle AA mode: None → FXAA → MSAA 2x → MSAA 4x → None
  B                   toggle bloom
  ESC                 release mouse / quit
"""

from __future__ import annotations

import math
import os
import sys

import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import glm

from grimoire3d.presentation.window import GameWindow
from grimoire3d.presentation.renderer3d import Renderer3D
from grimoire3d.models.render_settings_3d import RenderSettings3D
from grimoire3d.models.light3d import (
    AmbientLight,
    DirectionalLight,
    PointLight,
)
from grimoire3d.logic.camera3d import FreelookCamera

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VIRTUAL_W, VIRTUAL_H = 1920, 1080

# AA mode cycle order
AA_MODES = ("none", "fxaa", "msaa2x", "msaa4x")
AA_DISPLAY_NAMES = {
    "none": "None (OFF)",
    "fxaa": "FXAA",
    "msaa2x": "MSAA 2x",
    "msaa4x": "MSAA 4x",
}

# Grid ground plane
GRID_SIZE = 40.0
GRID_CELLS = 4

# Colors
GRID_LIGHT = (0.85, 0.85, 0.85, 1.0)
GRID_DARK = (0.15, 0.15, 0.15, 1.0)
BOX_COLORS = [
    (0.9, 0.2, 0.1, 1.0),
    (0.1, 0.6, 0.9, 1.0),
    (0.1, 0.8, 0.2, 1.0),
    (0.9, 0.8, 0.1, 1.0),
    (0.7, 0.2, 0.8, 1.0),
    (1.0, 0.5, 0.0, 1.0),
]
POLE_COLOR = (0.2, 0.2, 0.2, 1.0)


# ---------------------------------------------------------------------------
# Draw scene geometry
# ---------------------------------------------------------------------------


def draw_ground_grid(r3d: Renderer3D) -> None:
    """Draw a checkerboard ground plane — high contrast shows aliasing on edges."""
    cell_size = GRID_SIZE / GRID_CELLS
    half = GRID_SIZE / 2.0
    for row in range(GRID_CELLS):
        for col in range(GRID_CELLS):
            color = GRID_LIGHT if (row + col) % 2 == 0 else GRID_DARK
            x0 = -half + col * cell_size
            z0 = -half + row * cell_size
            x1 = x0 + cell_size
            z1 = z0 + cell_size
            r3d.draw_quad(
                (x0, 0, z0),
                (x1, 0, z0),
                (x1, 0, z1),
                (x0, 0, z1),
                color,
            )


def draw_rotated_boxes(r3d: Renderer3D, t: float) -> None:
    """Draw several boxes at various rotations — diagonal edges show stairstepping."""
    box_specs = [
        # (position, size, base_rotation_deg)
        ((-4.0, 1.0, -4.0), 1.5, 35.0),
        ((4.0, 1.5, -6.0), 1.2, 22.0),
        ((-6.0, 0.8, 5.0), 1.8, 50.0),
        ((5.0, 2.0, 4.0), 1.0, 67.0),
        ((0.0, 3.0, -8.0), 0.8, 15.0),
        ((-3.0, 1.2, 8.0), 1.4, 80.0),
    ]
    for i, (pos, size, base_rot) in enumerate(box_specs):
        # Slow rotation to show aliasing artifacts moving
        angle = math.radians(base_rot + t * 8.0 * (1.0 + i * 0.3))
        rot = glm.rotate(glm.mat4(1.0), angle, glm.vec3(0.0, 1.0, 0.0))
        color = BOX_COLORS[i % len(BOX_COLORS)]
        r3d.draw_box(
            pos,
            size=(size, size, size),
            color=color,
            rotation=rot,
        )


def draw_thin_poles(r3d: Renderer3D) -> None:
    """Draw thin cylinders — stairstepping is very visible on thin vertical objects."""
    pole_height = 6.0
    pole_radius = 0.04  # Very thin to exaggerate aliasing

    # Row of fence-like poles
    for i in range(8):
        x = -7.0 + i * 2.0
        r3d.draw_cylinder(
            (x, pole_height / 2.0, -10.0),
            radius=pole_radius,
            height=pole_height,
            color=POLE_COLOR,
        )

    # Diagonal arrangement
    for i in range(5):
        x = -3.0 + i * 2.0
        z = 6.0 + i * 1.5
        r3d.draw_cylinder(
            (x, pole_height / 2.0, z),
            radius=pole_radius,
            height=pole_height,
            color=POLE_COLOR,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> None:
    win = GameWindow(
        "Grimoire3D — Anti-Aliasing Demo",
        virtual_width=VIRTUAL_W,
        virtual_height=VIRTUAL_H,
        target_fps=60,
        bar_color=(0, 0, 0, 255),
    )

    settings = RenderSettings3D(
        specular=True,
        fog=False,
        shadows=True,
        bloom=False,
        bloom_threshold=0.8,
        bloom_intensity=0.15,
        gamma=2.2,
        brightness=1.0,
        aa_mode="none",
    )
    r3d = Renderer3D(win.ctx, settings)

    camera = FreelookCamera(
        position=(0.0, 4.0, 12.0),
        yaw=-90.0,
        pitch=-15.0,
        fov=75.0,
        speed=6.0,
        sensitivity=0.15,
    )

    ambient = AmbientLight(color=(0.25, 0.25, 0.28))
    sun = DirectionalLight(
        direction=(-0.4, -0.7, 0.5),
        color=(1.0, 0.95, 0.85),
        intensity=0.8,
        enabled=True,
    )

    # A few static point lights for extra edge contrast
    point_lights = [
        PointLight(
            position=(-6.0, 4.0, -6.0),
            color=(1.0, 0.8, 0.6),
            intensity=3.0,
            radius=12.0,
        ),
        PointLight(
            position=(6.0, 4.0, 6.0), color=(0.6, 0.8, 1.0), intensity=3.0, radius=12.0
        ),
        PointLight(
            position=(0.0, 5.0, 0.0), color=(1.0, 1.0, 1.0), intensity=2.0, radius=15.0
        ),
    ]

    mouse_captured = False
    keys_held: set[int] = set()
    pending_dx = pending_dy = 0.0
    anim_time: float = 0.0
    aa_index: int = 0  # index into AA_MODES

    VW = float(VIRTUAL_W)
    VH = float(VIRTUAL_H)

    while win.is_open:
        # --- Events ---
        pending_dx = pending_dy = 0.0
        for event in win.poll():
            if event.type == pygame.QUIT:
                win.close()
            elif event.type == pygame.KEYDOWN:
                keys_held.add(event.key)

                if event.key == pygame.K_ESCAPE:
                    if mouse_captured:
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                        mouse_captured = False
                    else:
                        win.close()

                # Cycle AA mode with key 1
                elif event.key == pygame.K_1:
                    aa_index = (aa_index + 1) % len(AA_MODES)
                    settings.aa_mode = AA_MODES[aa_index]
                    r3d._pp.refresh_msaa()

                # Toggle bloom
                elif event.key == pygame.K_b:
                    settings.bloom = not settings.bloom

            elif event.type == pygame.KEYUP:
                keys_held.discard(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not mouse_captured:
                    pygame.event.set_grab(True)
                    pygame.mouse.set_visible(False)
                    mouse_captured = True
            elif event.type == pygame.MOUSEMOTION and mouse_captured:
                pending_dx += event.rel[0]
                pending_dy += event.rel[1]

        # --- Frame start ---
        dt = win.begin_frame()
        anim_time += dt

        # --- Camera ---
        if mouse_captured and (pending_dx or pending_dy):
            camera.apply_mouse(pending_dx, pending_dy)

        if mouse_captured:
            fwd = camera.get_forward()
            right = camera.get_right()
            hvel = glm.vec3(0.0)
            if pygame.K_w in keys_held:
                hvel += fwd
            if pygame.K_s in keys_held:
                hvel -= fwd
            if pygame.K_a in keys_held:
                hvel -= right
            if pygame.K_d in keys_held:
                hvel += right
            if glm.length(hvel) > 0.001:
                hvel = glm.normalize(hvel)
            move = hvel * camera.speed * dt
            vv = 0.0
            if pygame.K_q in keys_held:
                vv += camera.speed
            if pygame.K_e in keys_held:
                vv -= camera.speed
            move.y += vv * dt
            camera.position += move

        # --- Render ---
        # Shadow pass
        if settings.shadows:
            r3d.begin_shadow_pass(
                sun,
                scene_center=(0.0, 3.0, 0.0),
                scene_radius=25.0,
            )
            draw_ground_grid(r3d)
            draw_rotated_boxes(r3d, anim_time)
            draw_thin_poles(r3d)
            r3d.end_shadow_pass()

        # Color pass
        r3d.begin_scene(
            camera,
            win.viewport,
            dt=dt,
            sky_color=(0.45, 0.60, 0.80, 1.0),
            ambient=ambient,
            dir_light=sun,
            point_lights=point_lights,
        )
        draw_ground_grid(r3d)
        draw_rotated_boxes(r3d, anim_time)
        draw_thin_poles(r3d)
        r3d.end_scene()

        # --- HUD ---
        r = win.renderer
        fps = win.fps
        aa_name = AA_DISPLAY_NAMES[settings.aa_mode]
        bloom_status = "ON " if settings.bloom else "OFF"

        r.draw_rect(0, 0, VW, 80, (0, 0, 0, 255))
        r.draw_text(
            f"Grimoire3D  AA Demo  |  FPS: {fps:5.1f}  |  AA Mode: {aa_name}",
            14,
            8,
            font_size=26,
            color=(0.9, 0.95, 1.0, 1.0),
        )
        r.draw_text(
            f"[1] Cycle AA: {aa_name}  [B] Bloom: {bloom_status}",
            14,
            38,
            font_size=18,
            color=(0.6, 0.70, 0.85, 1.0),
        )
        r.draw_text(
            "WASD+QE move  |  Click=capture  |  ESC=quit",
            14,
            60,
            font_size=16,
            color=(0.5, 0.55, 0.65, 1.0),
        )

        if not mouse_captured:
            r.draw_text(
                "Click to capture mouse",
                VW / 2 - 160,
                VH / 2 - 14,
                font_size=28,
                color=(1.0, 1.0, 0.5, 0.9),
            )

        win.end_frame()

    win.quit()


if __name__ == "__main__":
    run()
