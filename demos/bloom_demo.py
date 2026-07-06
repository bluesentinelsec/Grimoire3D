"""Bloom Demo — Post-Processing Showcase

A purpose-built scene with emissive bright sources to demonstrate the
bloom post-processing effect.  Toggle bloom on/off in real-time to see
the difference.

Scene: a dark room with brightly coloured animated point lights and
reflective pillars.  The darkness makes bloom clearly visible as light
bleeds into surrounding pixels.

Controls:
  Mouse               look (click to capture)
  WASD                strafe / walk
  Q / E               fly up / down
  B                   toggle bloom ON/OFF
  T / Y               decrease / increase bloom threshold (0.0 – 2.0)
  G / H               decrease / increase bloom intensity (0.0 – 2.0)
  [ / ]               decrease / increase gamma (0.5 – 3.0)
  - / =               decrease / increase brightness (0.1 – 2.0)
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

# Room dimensions
ROOM_W, ROOM_H, ROOM_L = 24.0, 6.0, 24.0

# Colors
FLOOR_COLOR = (0.18, 0.16, 0.14, 1.0)
WALL_COLOR = (0.15, 0.14, 0.16, 1.0)
CEIL_COLOR = (0.12, 0.11, 0.13, 1.0)


# ---------------------------------------------------------------------------
# Animated point lights — bright and colorful to show bloom
# ---------------------------------------------------------------------------


def _hue_to_rgb(hue: float) -> tuple[float, float, float]:
    """Convert a hue angle (radians) to an RGB color."""
    TWO_PI_3 = 2.0943951
    r = 0.5 + 0.5 * math.cos(hue)
    g = 0.5 + 0.5 * math.cos(hue + TWO_PI_3)
    b = 0.5 + 0.5 * math.cos(hue + 2 * TWO_PI_3)
    return (max(0.0, r), max(0.0, g), max(0.0, b))


def build_point_lights(t: float) -> list[PointLight]:
    """Create animated point lights that are bright enough to trigger bloom."""
    lights: list[PointLight] = []
    PI = math.pi

    # Ring of 8 lights floating in the centre of the room
    ring_y = 3.0
    ring_radius = 6.0
    for i in range(8):
        angle = 2 * PI * i / 8 + t * 0.3
        x = ROOM_W / 2 + ring_radius * math.cos(angle)
        z = ROOM_L / 2 + ring_radius * math.sin(angle)
        y = ring_y + 0.8 * math.sin(t * 1.5 + i * PI / 4)
        hue = t * 0.4 + i * PI / 4
        color = _hue_to_rgb(hue)
        pulse = 1.0 + 0.3 * math.sin(t * 2.0 + i)
        lights.append(
            PointLight(
                position=(x, y, z),
                color=color,
                intensity=5.0 * pulse,
                radius=12.0,
            )
        )

    # 4 corner floor lights — warm tones, very bright
    corners = [
        (2.0, 0.5, 2.0),
        (ROOM_W - 2.0, 0.5, 2.0),
        (2.0, 0.5, ROOM_L - 2.0),
        (ROOM_W - 2.0, 0.5, ROOM_L - 2.0),
    ]
    for i, pos in enumerate(corners):
        pulse = 1.0 + 0.5 * math.sin(t * 1.2 + i * PI / 2)
        lights.append(
            PointLight(
                position=pos,
                color=(1.0, 0.6, 0.2),
                intensity=4.0 * pulse,
                radius=10.0,
            )
        )

    # Central overhead bright white light
    lights.append(
        PointLight(
            position=(ROOM_W / 2, ROOM_H - 0.5, ROOM_L / 2),
            color=(1.0, 1.0, 1.0),
            intensity=6.0 + 2.0 * math.sin(t * 0.8),
            radius=16.0,
        )
    )

    return lights


# ---------------------------------------------------------------------------
# Draw scene geometry
# ---------------------------------------------------------------------------


def draw_room(r3d: Renderer3D) -> None:
    """Draw a simple dark room as a backdrop for the bloom lights."""
    W, H, L = ROOM_W, ROOM_H, ROOM_L

    # Floor
    r3d.draw_quad((0, 0, 0), (W, 0, 0), (W, 0, L), (0, 0, L), FLOOR_COLOR)
    # Ceiling
    r3d.draw_quad((0, H, L), (W, H, L), (W, H, 0), (0, H, 0), CEIL_COLOR)
    # Walls
    r3d.draw_quad((0, 0, 0), (0, 0, L), (0, H, L), (0, H, 0), WALL_COLOR)
    r3d.draw_quad((W, 0, L), (W, 0, 0), (W, H, 0), (W, H, L), WALL_COLOR)
    r3d.draw_quad((0, 0, 0), (W, 0, 0), (W, H, 0), (0, H, 0), WALL_COLOR)
    r3d.draw_quad((W, 0, L), (0, 0, L), (0, H, L), (W, H, L), WALL_COLOR)

    # Reflective pillars
    for px, pz in [(6, 6), (18, 6), (6, 18), (18, 18), (12, 12)]:
        r3d.draw_cylinder(
            (px, H / 2, pz),
            radius=0.3,
            height=H,
            color=(0.15, 0.15, 0.18, 1.0),
        )

    # Bright sphere at the centre (catches light nicely)
    r3d.draw_sphere(
        (ROOM_W / 2, ROOM_H - 0.5, ROOM_L / 2),
        radius=0.3,
        color=(1.0, 1.0, 1.0, 1.0),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> None:
    win = GameWindow(
        "Grimoire3D — Bloom Demo",
        virtual_width=VIRTUAL_W,
        virtual_height=VIRTUAL_H,
        target_fps=60,
        bar_color=(0, 0, 0, 255),
    )

    settings = RenderSettings3D(
        specular=True,
        fog=False,
        shadows=True,
        bloom=True,
        bloom_threshold=0.3,
        bloom_intensity=0.2,
        gamma=2.2,
        brightness=1.0,
    )
    r3d = Renderer3D(win.ctx, settings)

    camera = FreelookCamera(
        position=(ROOM_W / 2, 2.5, 3.0),
        yaw=90.0,
        pitch=-5.0,
        fov=80.0,
        speed=5.0,
        sensitivity=0.15,
    )

    ambient = AmbientLight(color=(0.08, 0.08, 0.10))
    sun = DirectionalLight(
        direction=(-0.3, -0.8, 0.5),
        color=(0.8, 0.85, 0.9),
        intensity=0.3,
        enabled=True,
    )

    mouse_captured = False
    keys_held: set[int] = set()
    pending_dx = pending_dy = 0.0
    anim_time: float = 0.0

    VW = float(VIRTUAL_W)
    VH = float(VIRTUAL_H)

    while win.is_open:
        # --- Events (use win.poll() like all other demos) ---
        pending_dx = pending_dy = 0.0
        for event in win.poll():
            if event.type == pygame.QUIT:
                win.close()
            elif event.type == pygame.KEYDOWN:
                keys_held.add(event.key)
                shift = bool(event.mod & pygame.KMOD_SHIFT)

                if event.key == pygame.K_ESCAPE:
                    if mouse_captured:
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                        mouse_captured = False
                    else:
                        win.close()

                # Bloom controls
                elif event.key == pygame.K_b:
                    settings.bloom = not settings.bloom
                elif event.key == pygame.K_t:
                    settings.bloom_threshold = round(
                        max(0.0, settings.bloom_threshold - 0.1), 2
                    )
                elif event.key == pygame.K_y:
                    settings.bloom_threshold = round(
                        min(2.0, settings.bloom_threshold + 0.1), 2
                    )
                elif event.key == pygame.K_g and not shift:
                    settings.bloom_intensity = round(
                        max(0.0, settings.bloom_intensity - 0.05), 2
                    )
                elif event.key == pygame.K_h and not shift:
                    settings.bloom_intensity = round(
                        min(2.0, settings.bloom_intensity + 0.05), 2
                    )

                # Gamma / brightness
                elif event.key == pygame.K_LEFTBRACKET:
                    settings.gamma = round(max(0.5, settings.gamma - 0.1), 2)
                elif event.key == pygame.K_RIGHTBRACKET:
                    settings.gamma = round(min(3.0, settings.gamma + 0.1), 2)
                elif event.key == pygame.K_MINUS:
                    settings.brightness = round(max(0.1, settings.brightness - 0.05), 2)
                elif event.key == pygame.K_EQUALS:
                    settings.brightness = round(min(2.0, settings.brightness + 0.05), 2)

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
        point_lights = build_point_lights(anim_time)

        # Shadow pass
        if settings.shadows:
            r3d.begin_shadow_pass(
                sun,
                scene_center=(ROOM_W / 2, ROOM_H / 2, ROOM_L / 2),
                scene_radius=20.0,
            )
            draw_room(r3d)
            r3d.end_shadow_pass()

        # Color pass
        r3d.begin_scene(
            camera,
            win.viewport,
            dt=dt,
            sky_color=(0.0, 0.0, 0.0, 1.0),
            ambient=ambient,
            dir_light=sun,
            point_lights=point_lights,
        )
        draw_room(r3d)
        r3d.end_scene()

        # --- HUD ---
        r = win.renderer
        fps = win.fps
        bloom_status = "ON " if settings.bloom else "OFF"

        r.draw_rect(0, 0, VW, 80, (0, 0, 0, 255))
        r.draw_text(
            f"Grimoire3D  Bloom Demo  |  FPS: {fps:5.1f}",
            14,
            8,
            font_size=26,
            color=(0.9, 0.95, 1.0, 1.0),
        )
        r.draw_text(
            f"[B] Bloom: {bloom_status}  "
            f"[T/Y] Threshold: {settings.bloom_threshold:.2f}  "
            f"[G/H] Intensity: {settings.bloom_intensity:.2f}  "
            f"[[ ]] Gamma: {settings.gamma:.1f}  "
            f"[- =] Bright: {settings.brightness:.2f}",
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
