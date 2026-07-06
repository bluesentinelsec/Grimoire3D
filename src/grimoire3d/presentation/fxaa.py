"""FXAA post-processing pass.

Fast Approximate Anti-Aliasing — a single fullscreen shader pass that
detects high-contrast edges via luminance sampling and blends them to
reduce aliasing artifacts.

The pass reads from the scene texture, applies FXAA, and writes the
result back into the scene FBO. A ping texture is used to avoid the
read-write feedback loop.
"""

from __future__ import annotations

import logging

import moderngl

from grimoire3d.models.render_settings_3d import RenderSettings3D
from grimoire3d.presentation.shaders3d import BLIT_VERT, FXAA_FRAG

logger = logging.getLogger(__name__)


class FxaaPass:
    """Single-pass FXAA at full scene resolution."""

    def __init__(self, ctx: moderngl.Context, settings: RenderSettings3D) -> None:
        self._ctx = ctx
        self._settings = settings

        self._prog = ctx.program(vertex_shader=BLIT_VERT, fragment_shader=FXAA_FRAG)
        self._prog["u_scene"].value = 0
        self._vao = ctx.vertex_array(self._prog, [])

        # Ping texture: copy scene here, then run FXAA reading it back to scene
        self._ping_tex: moderngl.Texture | None = None
        self._ping_fbo: moderngl.Framebuffer | None = None
        self._w = 0
        self._h = 0

    def ensure_size(self, width: int, height: int) -> None:
        """Rebuild the ping texture if dimensions changed."""
        if width == self._w and height == self._h:
            return
        self._rebuild(width, height)

    def _rebuild(self, width: int, height: int) -> None:
        """Release and recreate the ping texture and FBO."""
        self._release()
        self._w = width
        self._h = height
        self._ping_tex = self._ctx.texture((width, height), 4, dtype="f2")
        self._ping_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._ping_fbo = self._ctx.framebuffer(color_attachments=[self._ping_tex])

    def _release(self) -> None:
        """Free GPU resources."""
        if self._ping_fbo is not None:
            self._ping_fbo.release()
        if self._ping_tex is not None:
            self._ping_tex.release()
        self._ping_tex = None
        self._ping_fbo = None

    def execute(
        self,
        scene_color: moderngl.Texture,
        scene_fbo: moderngl.Framebuffer,
        width: int,
        height: int,
    ) -> None:
        """Run FXAA on the scene.

        Copies scene_color to a ping texture, then renders FXAA reading
        from ping back into scene_fbo. After this call, scene_color
        contains the anti-aliased image.
        """
        w, h = width, height

        # Step 1: Copy scene_color -> ping_tex
        # With texel_size=(0,0) all neighbor samples equal the center texel,
        # so lumaRange=0 < threshold causing the shader to early-exit with
        # the original color — effectively a perfect passthrough copy.
        self._ping_fbo.use()
        self._ctx.viewport = (0, 0, w, h)
        scene_color.use(0)
        self._prog["u_texel_size"].value = (0.0, 0.0)
        self._vao.render(moderngl.TRIANGLES, vertices=3)

        # Step 2: Run FXAA reading ping_tex -> writing to scene_fbo
        scene_fbo.use()
        self._ctx.viewport = (0, 0, w, h)
        self._ping_tex.use(0)
        self._prog["u_texel_size"].value = (1.0 / w, 1.0 / h)
        self._vao.render(moderngl.TRIANGLES, vertices=3)

    def release(self) -> None:
        """Release all GPU resources."""
        self._release()
        self._vao.release()
        self._prog.release()
