"""Unit tests for the anti-aliasing feature.

Tests cover:
- RenderSettings3D aa_mode field (model layer, no GL)
- FXAA shader source validity (basic syntax checks)
- FxaaPass construction and size management logic
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


class TestAASettings(unittest.TestCase):
    """Test aa_mode field on RenderSettings3D."""

    def test_default_is_none(self):
        s = RenderSettings3D()
        self.assertEqual(s.aa_mode, "none")

    def test_set_fxaa(self):
        s = RenderSettings3D(aa_mode="fxaa")
        self.assertEqual(s.aa_mode, "fxaa")

    def test_set_msaa2x(self):
        s = RenderSettings3D(aa_mode="msaa2x")
        self.assertEqual(s.aa_mode, "msaa2x")

    def test_set_msaa4x(self):
        s = RenderSettings3D(aa_mode="msaa4x")
        self.assertEqual(s.aa_mode, "msaa4x")

    def test_replace_aa_mode(self):
        """dataclass replace works for runtime adjustment."""
        s = RenderSettings3D()
        s2 = replace(s, aa_mode="fxaa")
        self.assertEqual(s2.aa_mode, "fxaa")
        # Original unchanged
        self.assertEqual(s.aa_mode, "none")

    def test_replace_to_msaa4x(self):
        s = RenderSettings3D(aa_mode="fxaa")
        s2 = replace(s, aa_mode="msaa4x")
        self.assertEqual(s2.aa_mode, "msaa4x")
        self.assertEqual(s.aa_mode, "fxaa")

    def test_other_fields_unaffected(self):
        """Setting aa_mode does not break existing fields."""
        s = RenderSettings3D(
            specular=False, fog=True, gamma=1.8, bloom=True, aa_mode="msaa2x"
        )
        self.assertFalse(s.specular)
        self.assertTrue(s.fog)
        self.assertEqual(s.gamma, 1.8)
        self.assertTrue(s.bloom)
        self.assertEqual(s.aa_mode, "msaa2x")

    def test_old_fxaa_field_does_not_exist(self):
        """The old boolean 'fxaa' field has been replaced by aa_mode."""
        s = RenderSettings3D()
        self.assertFalse(hasattr(s, "fxaa"))


class TestFxaaShaderSource(unittest.TestCase):
    """Verify FXAA_FRAG shader constant is defined and syntactically valid."""

    def test_fxaa_frag_exists(self):
        from grimoire3d.presentation.shaders3d import FXAA_FRAG

        self.assertIsInstance(FXAA_FRAG, str)

    def test_has_version_330_core(self):
        from grimoire3d.presentation.shaders3d import FXAA_FRAG

        self.assertIn("#version 330 core", FXAA_FRAG)

    def test_has_u_scene_uniform(self):
        from grimoire3d.presentation.shaders3d import FXAA_FRAG

        self.assertIn("u_scene", FXAA_FRAG)

    def test_has_u_texel_size_uniform(self):
        from grimoire3d.presentation.shaders3d import FXAA_FRAG

        self.assertIn("u_texel_size", FXAA_FRAG)

    def test_has_frag_color_output(self):
        from grimoire3d.presentation.shaders3d import FXAA_FRAG

        self.assertIn("frag_color", FXAA_FRAG)


class TestFxaaPassModule(unittest.TestCase):
    """Test FxaaPass class importability and size management."""

    def test_import(self):
        from grimoire3d.presentation.fxaa import FxaaPass

        self.assertTrue(callable(FxaaPass))

    def test_ensure_size_stores_dimensions(self):
        """Verify FxaaPass stores width/height after ensure_size."""
        from grimoire3d.presentation.fxaa import FxaaPass

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

        settings = RenderSettings3D(aa_mode="fxaa")
        fxaa = FxaaPass(mock_ctx, settings)

        # Before ensure_size, dimensions are 0
        self.assertEqual(fxaa._w, 0)
        self.assertEqual(fxaa._h, 0)

        # After ensure_size with 1920x1080, FXAA runs at full resolution
        fxaa.ensure_size(1920, 1080)
        self.assertEqual(fxaa._w, 1920)
        self.assertEqual(fxaa._h, 1080)

    def test_ensure_size_no_rebuild_same_dimensions(self):
        """Calling ensure_size again with same dimensions does not rebuild."""
        from grimoire3d.presentation.fxaa import FxaaPass

        mock_ctx = MagicMock()
        mock_prog = MagicMock()
        mock_ctx.program.return_value = mock_prog
        mock_prog.__getitem__ = MagicMock(return_value=MagicMock())
        mock_ctx.vertex_array.return_value = MagicMock()

        mock_tex = MagicMock()
        mock_tex.filter = (None, None)
        mock_ctx.texture.return_value = mock_tex
        mock_ctx.framebuffer.return_value = MagicMock()

        settings = RenderSettings3D(aa_mode="fxaa")
        fxaa = FxaaPass(mock_ctx, settings)
        fxaa.ensure_size(1920, 1080)

        # Reset mock counters
        mock_ctx.texture.reset_mock()
        fxaa.ensure_size(1920, 1080)
        mock_ctx.texture.assert_not_called()

    def test_ensure_size_rebuilds_on_new_dimensions(self):
        """Calling ensure_size with different dimensions triggers rebuild."""
        from grimoire3d.presentation.fxaa import FxaaPass

        mock_ctx = MagicMock()
        mock_prog = MagicMock()
        mock_ctx.program.return_value = mock_prog
        mock_prog.__getitem__ = MagicMock(return_value=MagicMock())
        mock_ctx.vertex_array.return_value = MagicMock()

        mock_tex = MagicMock()
        mock_tex.filter = (None, None)
        mock_ctx.texture.return_value = mock_tex
        mock_ctx.framebuffer.return_value = MagicMock()

        settings = RenderSettings3D(aa_mode="fxaa")
        fxaa = FxaaPass(mock_ctx, settings)
        fxaa.ensure_size(1920, 1080)

        # Different size triggers rebuild
        fxaa.ensure_size(1280, 720)
        self.assertEqual(fxaa._w, 1280)
        self.assertEqual(fxaa._h, 720)


if __name__ == "__main__":
    unittest.main()
