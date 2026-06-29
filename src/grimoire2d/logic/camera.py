"""Camera for mapping world coordinates to screen (physical) pixels.

The game logic and entities live in abstract "world units".
The Camera defines how those units map to physical screen pixels at render time.

This allows rendering the world directly at the display's native (or scaled)
resolution while the game logic remains independent of pixels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Camera:
    """Simple 2D camera.

    x, y: world position of the camera center.
    zoom: how many screen pixels one world unit occupies.
          zoom=1.0 means 1 world unit = 1 physical pixel (1:1).
          Higher zoom = more zoomed in (larger sprites).
          Lower zoom = zoomed out (more world visible).

    To achieve "same world visible on larger display", increase zoom
    proportionally to physical size.
    """

    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0

    def world_to_screen(
        self, world_x: float, world_y: float, screen_cx: float, screen_cy: float
    ) -> Tuple[float, float]:
        """Convert world coordinates to screen pixel coordinates.

        screen_cx, screen_cy: center of the screen/viewport in physical pixels.
        """
        sx = (world_x - self.x) * self.zoom + screen_cx
        sy = (world_y - self.y) * self.zoom + screen_cy
        return sx, sy

    def screen_to_world(
        self, screen_x: float, screen_y: float, screen_cx: float, screen_cy: float
    ) -> Tuple[float, float]:
        """Inverse of world_to_screen."""
        wx = (screen_x - screen_cx) / self.zoom + self.x
        wy = (screen_y - screen_cy) / self.zoom + self.y
        return wx, wy

    def with_updates(self, **changes) -> Camera:
        return Camera(
            x=changes.get("x", self.x),
            y=changes.get("y", self.y),
            zoom=changes.get("zoom", self.zoom),
        )
