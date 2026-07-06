"""Bloom post-processing pass.

Extracts bright pixels from the HDR scene buffer, applies iterative
Gaussian blur at half resolution, then composites the glow back onto
the scene additively.

The pass is fully self-contained and owns its own FBOs and programs.
It is instantiated by _PostProcessPipeline and called during run().
"""

from __future__ import annotations

import logging

import moderngl

from grimoire3d.models.render_settings_3d import RenderSettings3D
from grimoire3d.presentation.shaders3d import (
    BLIT_VERT,
    BLOOM_BRIGHT_FRAG,
    BLOOM_BLUR_FRAG,
    BLOOM_COMPOSITE_FRAG,
)

logger = logging.getLogger(__name__)


class BloomPass:
    """Multi-pass Gaussian bloom at half scene resolution."""

    BLUR_ITERATIONS = 5

    def __init__(self, ctx: moderngl.Context, settings: RenderSettings3D) -> None:
        self._ctx = ctx
        self._settings = settings

        # Compile shader programs
        self._bright_prog = ctx.program(
            vertex_shader=BLIT_VERT, fragment_shader=BLOOM_BRIGHT_FRAG
        )
        self._blur_prog = ctx.program(
            vertex_shader=BLIT_VERT, fragment_shader=BLOOM_BLUR_FRAG
        )
        self._composite_prog = ctx.program(
            vertex_shader=BLIT_VERT, fragment_shader=BLOOM_COMPOSITE_FRAG
        )

        # Texture unit assignments
        self._bright_prog["u_scene"].value = 0
        self._blur_prog["u_input"].value = 0
        self._composite_prog["u_bloom"].value = 1

        # Empty VAOs (covering triangle uses gl_VertexID)
        self._bright_vao = ctx.vertex_array(self._bright_prog, [])
        self._blur_vao = ctx.vertex_array(self._blur_prog, [])
        self._composite_vao = ctx.vertex_array(self._composite_prog, [])

        # FBO state (allocated on first ensure_size)
        self._bloom_tex: moderngl.Texture | None = None
        self._bloom_fbo: moderngl.Framebuffer | None = None
        self._ping_tex: moderngl.Texture | None = None
        self._ping_fbo: moderngl.Framebuffer | None = None
        self._w = 0
        self._h = 0

    def ensure_size(self, scene_width: int, scene_height: int) -> None:
        """Rebuild bloom FBOs if scene dimensions changed."""
        # Bloom operates at half resolution
        w = max(1, scene_width // 2)
        h = max(1, scene_height // 2)
        if w == self._w and h == self._h:
            return
        self._rebuild(w, h)

    def _rebuild(self, width: int, height: int) -> None:
        """Release and recreate bloom textures and FBOs."""
        self._release()
        self._w = width
        self._h = height

        # RGBA16F for HDR bloom values
        self._bloom_tex = self._ctx.texture((width, height), 4, dtype="f2")
        self._bloom_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._bloom_fbo = self._ctx.framebuffer(color_attachments=[self._bloom_tex])

        self._ping_tex = self._ctx.texture((width, height), 4, dtype="f2")
        self._ping_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._ping_fbo = self._ctx.framebuffer(color_attachments=[self._ping_tex])

    def _release(self) -> None:
        """Free GPU resources."""
        for obj in (self._bloom_fbo, self._bloom_tex, self._ping_fbo, self._ping_tex):
            if obj is not None:
                obj.release()
        self._bloom_tex = None
        self._bloom_fbo = None
        self._ping_tex = None
        self._ping_fbo = None

    def execute(
        self,
        scene_color: moderngl.Texture,
        scene_fbo: moderngl.Framebuffer,
        scene_width: int,
        scene_height: int,
    ) -> None:
        """Run the bloom pipeline.

        Reads bright pixels from *scene_color*, blurs them, and composites
        the result back into *scene_fbo*.
        """
        s = self._settings
        w, h = self._w, self._h

        # Step 1: Bright-pass extraction
        self._bloom_fbo.use()
        self._ctx.viewport = (0, 0, w, h)
        scene_color.use(0)
        self._bright_prog["u_threshold"].value = float(s.bloom_threshold)
        self._bright_vao.render(moderngl.TRIANGLES, vertices=3)

        # Step 2: Iterative Gaussian blur (ping-pong)
        for _i in range(self.BLUR_ITERATIONS):
            # Horizontal: bloom → ping
            self._ping_fbo.use()
            self._ctx.viewport = (0, 0, w, h)
            self._bloom_tex.use(0)
            self._blur_prog["u_direction"].value = (1.0 / w, 0.0)
            self._blur_vao.render(moderngl.TRIANGLES, vertices=3)
            # Vertical: ping → bloom
            self._bloom_fbo.use()
            self._ctx.viewport = (0, 0, w, h)
            self._ping_tex.use(0)
            self._blur_prog["u_direction"].value = (0.0, 1.0 / h)
            self._blur_vao.render(moderngl.TRIANGLES, vertices=3)

        # Step 3: Composite bloom onto scene (additive blending)
        # Use GL blending to add bloom on top of the existing scene content
        # in the FBO, avoiding the read-write feedback loop of sampling
        # scene_color while rendering to scene_fbo.
        scene_fbo.use()
        self._ctx.viewport = (0, 0, scene_width, scene_height)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.ONE, moderngl.ONE
        self._bloom_tex.use(1)
        self._composite_prog["u_intensity"].value = float(s.bloom_intensity)
        self._composite_vao.render(moderngl.TRIANGLES, vertices=3)
        self._ctx.disable(moderngl.BLEND)

    def release(self) -> None:
        """Release all GPU resources owned by this pass."""
        self._release()
        for vao in (self._bright_vao, self._blur_vao, self._composite_vao):
            vao.release()
        for prog in (self._bright_prog, self._blur_prog, self._composite_prog):
            prog.release()
