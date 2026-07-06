"""Unit tests for the bloom post-processing feature.

Tests cover:
- RenderSettings3D bloom fields (model layer, no GL)
- BloomPass construction and size management logic
- Shader source validity (basic syntax checks)
"""

import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

# Support running tests directly before `pip install -e .`
_src = Path(__file__).parent.parent / "src"
if _src.exists():
    sys.path.insert(0, str(_src))

from grimoire3d.models.render_settings_3d import RenderSettings3D


class TestBloomSettings(unittest.TestCase):
    """Test bloom-related fields on RenderSettings3D."""

    def test_defaults(self):
        s = RenderSettings3D()
        self.assertFalse(s.bloom)
        self.assertEqual(s.bloom_threshold, 1.0)
        self.assertEqual(s.bloom_intensity, 0.3)

    def test_bloom_enabled(self):
        s = RenderSettings3D(bloom=True)
        self.assertTrue(s.bloom)

    def test_custom_threshold_and_intensity(self):
        s = RenderSettings3D(bloom=True, bloom_threshold=0.8, bloom_intensity=1.5)
        self.assertEqual(s.bloom_threshold, 0.8)
        self.assertEqual(s.bloom_intensity, 1.5)

    def test_threshold_zero(self):
        """Zero threshold means everything contributes to bloom."""
        s = RenderSettings3D(bloom=True, bloom_threshold=0.0)
        self.assertEqual(s.bloom_threshold, 0.0)

    def test_intensity_zero_effectively_disables(self):
        """Zero intensity means bloom is computed but adds nothing."""
        s = RenderSettings3D(bloom=True, bloom_intensity=0.0)
        self.assertEqual(s.bloom_intensity, 0.0)

    def test_replace_bloom_fields(self):
        """dataclass replace works for runtime adjustment."""
        s = RenderSettings3D()
        s2 = replace(s, bloom=True, bloom_threshold=0.5, bloom_intensity=0.8)
        self.assertTrue(s2.bloom)
        self.assertEqual(s2.bloom_threshold, 0.5)
        self.assertEqual(s2.bloom_intensity, 0.8)
        # Original unchanged
        self.assertFalse(s.bloom)

    def test_other_fields_unaffected(self):
        """Adding bloom fields does not break existing fields."""
        s = RenderSettings3D(specular=False, fog=True, gamma=1.8, bloom=True)
        self.assertFalse(s.specular)
        self.assertTrue(s.fog)
        self.assertEqual(s.gamma, 1.8)
        self.assertTrue(s.bloom)


class TestBloomShaderSources(unittest.TestCase):
    """Verify bloom shader constants are defined and syntactically valid."""

    def test_shader_constants_exist(self):
        from grimoire3d.presentation.shaders3d import (
            BLOOM_BRIGHT_FRAG,
            BLOOM_BLUR_FRAG,
            BLOOM_COMPOSITE_FRAG,
        )

        self.assertIsInstance(BLOOM_BRIGHT_FRAG, str)
        self.assertIsInstance(BLOOM_BLUR_FRAG, str)
        self.assertIsInstance(BLOOM_COMPOSITE_FRAG, str)

    def test_shader_version_directive(self):
        from grimoire3d.presentation.shaders3d import (
            BLOOM_BRIGHT_FRAG,
            BLOOM_BLUR_FRAG,
            BLOOM_COMPOSITE_FRAG,
        )

        for name, src in [
            ("BLOOM_BRIGHT_FRAG", BLOOM_BRIGHT_FRAG),
            ("BLOOM_BLUR_FRAG", BLOOM_BLUR_FRAG),
            ("BLOOM_COMPOSITE_FRAG", BLOOM_COMPOSITE_FRAG),
        ]:
            with self.subTest(shader=name):
                self.assertIn("#version 330 core", src)

    def test_bright_shader_has_threshold_uniform(self):
        from grimoire3d.presentation.shaders3d import BLOOM_BRIGHT_FRAG

        self.assertIn("u_threshold", BLOOM_BRIGHT_FRAG)
        self.assertIn("u_scene", BLOOM_BRIGHT_FRAG)

    def test_blur_shader_has_direction_uniform(self):
        from grimoire3d.presentation.shaders3d import BLOOM_BLUR_FRAG

        self.assertIn("u_direction", BLOOM_BLUR_FRAG)
        self.assertIn("u_input", BLOOM_BLUR_FRAG)

    def test_composite_shader_has_intensity_uniform(self):
        from grimoire3d.presentation.shaders3d import BLOOM_COMPOSITE_FRAG

        self.assertIn("u_intensity", BLOOM_COMPOSITE_FRAG)
        self.assertIn("u_scene", BLOOM_COMPOSITE_FRAG)
        self.assertIn("u_bloom", BLOOM_COMPOSITE_FRAG)

    def test_shaders_have_output(self):
        from grimoire3d.presentation.shaders3d import (
            BLOOM_BRIGHT_FRAG,
            BLOOM_BLUR_FRAG,
            BLOOM_COMPOSITE_FRAG,
        )

        for name, src in [
            ("BLOOM_BRIGHT_FRAG", BLOOM_BRIGHT_FRAG),
            ("BLOOM_BLUR_FRAG", BLOOM_BLUR_FRAG),
            ("BLOOM_COMPOSITE_FRAG", BLOOM_COMPOSITE_FRAG),
        ]:
            with self.subTest(shader=name):
                self.assertIn("frag_color", src)


class TestBloomPassModule(unittest.TestCase):
    """Test BloomPass class importability and constants."""

    def test_import(self):
        from grimoire3d.presentation.bloom import BloomPass

        self.assertTrue(hasattr(BloomPass, "BLUR_ITERATIONS"))

    def test_blur_iterations_constant(self):
        from grimoire3d.presentation.bloom import BloomPass

        self.assertEqual(BloomPass.BLUR_ITERATIONS, 5)

    def test_ensure_size_math(self):
        """Verify half-resolution calculation logic.

        BloomPass.ensure_size divides scene dimensions by 2.
        We test the math without needing a real GL context by checking
        that the class stores the expected dimensions.
        """
        from grimoire3d.presentation.bloom import BloomPass

        # Mock the GL context to avoid needing a real one
        mock_ctx = MagicMock()
        mock_prog = MagicMock()
        mock_ctx.program.return_value = mock_prog
        mock_prog.__getitem__ = MagicMock(return_value=MagicMock())
        mock_ctx.vertex_array.return_value = MagicMock()

        # Mock texture and framebuffer creation
        mock_tex = MagicMock()
        mock_tex.filter = (None, None)
        mock_ctx.texture.return_value = mock_tex
        mock_fbo = MagicMock()
        mock_ctx.framebuffer.return_value = mock_fbo

        settings = RenderSettings3D(bloom=True)
        bloom = BloomPass(mock_ctx, settings)

        # Before ensure_size, dimensions are 0
        self.assertEqual(bloom._w, 0)
        self.assertEqual(bloom._h, 0)

        # After ensure_size with 1920x1080, bloom should be 960x540
        bloom.ensure_size(1920, 1080)
        self.assertEqual(bloom._w, 960)
        self.assertEqual(bloom._h, 540)

        # Calling again with same size should not rebuild
        mock_ctx.texture.reset_mock()
        bloom.ensure_size(1920, 1080)
        mock_ctx.texture.assert_not_called()

        # Different size triggers rebuild
        bloom.ensure_size(1280, 720)
        self.assertEqual(bloom._w, 640)
        self.assertEqual(bloom._h, 360)

    def test_minimum_size_clamped(self):
        """Bloom dimensions never go below 1x1."""
        from grimoire3d.presentation.bloom import BloomPass

        mock_ctx = MagicMock()
        mock_prog = MagicMock()
        mock_ctx.program.return_value = mock_prog
        mock_prog.__getitem__ = MagicMock(return_value=MagicMock())
        mock_ctx.vertex_array.return_value = MagicMock()
        mock_tex = MagicMock()
        mock_tex.filter = (None, None)
        mock_ctx.texture.return_value = mock_tex
        mock_ctx.framebuffer.return_value = MagicMock()

        settings = RenderSettings3D(bloom=True)
        bloom = BloomPass(mock_ctx, settings)
        bloom.ensure_size(1, 1)
        self.assertGreaterEqual(bloom._w, 1)
        self.assertGreaterEqual(bloom._h, 1)


if __name__ == "__main__":
    unittest.main()
