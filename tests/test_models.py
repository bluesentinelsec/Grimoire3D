"""Unit tests for the pure data model layer (Chunk 1).

Uses only the standard library (unittest + dataclasses).
No caller logic, no VFS, no presentation or logic layers involved.
Tests are isolated to models/ only.

These tests verify the *maximum* OCP design:
- EngineConfig has NO hard-coded members besides the extensions mechanism.
- ALL configuration (including what used to be direct fields) lives in extensions.
- Every addition is purely net-new (new model + register_extension).
"""

import sys
import unittest
from dataclasses import dataclass, field, replace
from pathlib import Path

# Support running tests directly or via discover before `pip install -e .`
_src = Path(__file__).parent.parent / "src"
if _src.exists():
    sys.path.insert(0, str(_src))

from grimoire2d.models import (
    EngineConfig,
    DataModel,
    TitleSetting,
    VideoSettings,
    TimingSettings,
    register_extension,
)


class TestTitleSetting(unittest.TestCase):
    def test_defaults(self):
        t = TitleSetting()
        self.assertEqual(t.value, "Grimoire2D")


class TestVideoSettings(unittest.TestCase):
    def test_defaults_and_validation(self):
        v = VideoSettings()
        self.assertEqual(v.width, 800)
        with self.assertRaises(ValueError):
            VideoSettings(width=0)

    def test_with_updates_and_serialization(self):
        v = VideoSettings(width=640)
        updated = v.with_updates(height=480)
        self.assertEqual(updated.height, 480)
        d = updated.to_dict()
        restored = VideoSettings.from_dict(d)
        self.assertEqual(restored, updated)


class TestTimingSettings(unittest.TestCase):
    def test_defaults_and_validation(self):
        t = TimingSettings()
        self.assertEqual(t.target_fps, 60)
        with self.assertRaises(ValueError):
            TimingSettings(target_fps=0)


class TestEngineConfigPureExtensions(unittest.TestCase):
    def test_default_populates_from_registry(self):
        cfg = EngineConfig.default()
        self.assertIn("title", cfg.extensions)
        self.assertIn("video", cfg.extensions)
        self.assertIn("timing", cfg.extensions)
        self.assertIsInstance(cfg.extensions["title"], TitleSetting)
        self.assertIsInstance(cfg.extensions["video"], VideoSettings)
        self.assertIsInstance(cfg.extensions["timing"], TimingSettings)
        self.assertEqual(cfg.extensions["title"].value, "Grimoire2D")
        self.assertEqual(cfg.extensions["video"].width, 800)

    def test_no_hard_coded_members(self):
        cfg = EngineConfig.default()
        # Only version and extensions should exist as fields
        self.assertTrue(hasattr(cfg, "version"))
        self.assertTrue(hasattr(cfg, "extensions"))
        # Accessing old-style direct attributes should fail (they are now in extensions)
        with self.assertRaises(AttributeError):
            _ = cfg.title
        with self.assertRaises(AttributeError):
            _ = cfg.video

    def test_access_via_extensions(self):
        cfg = EngineConfig.default()
        self.assertEqual(cfg.extensions["title"].value, "Grimoire2D")
        self.assertEqual(cfg.extensions["video"].width, 800)
        self.assertEqual(cfg.extensions["timing"].target_fps, 60)

    def test_to_dict_from_dict_roundtrip(self):
        cfg = EngineConfig.default()
        d = cfg.to_dict()
        restored = EngineConfig.from_dict(d)
        self.assertEqual(restored.extensions["title"].value, "Grimoire2D")
        self.assertEqual(restored.extensions["video"].width, 800)

    def test_with_updates_on_extensions(self):
        cfg = EngineConfig.default()
        updated = cfg.with_updates(video={"width": 1280}, title={"value": "New Title"})
        self.assertEqual(updated.extensions["video"].width, 1280)
        self.assertEqual(updated.extensions["title"].value, "New Title")
        self.assertEqual(cfg.extensions["video"].width, 800)  # original unchanged

    def test_adding_new_extension_is_net_new(self):
        # Simulate adding a completely new category without touching EngineConfig
        @dataclass(frozen=True, slots=True)
        class AudioSettings(DataModel):
            master_volume: float = 1.0
            version: int = 1

            def to_dict(self):
                return {"master_volume": self.master_volume, "version": self.version}

            @classmethod
            def from_dict(cls, data):
                return cls(master_volume=data.get("master_volume", 1.0), version=data.get("version", 1))

            def with_updates(self, **changes):
                return replace(self, **changes)

        # This call would live in the new audio.py file - no change to config.py or EngineConfig
        register_extension("audio", AudioSettings)

        cfg = EngineConfig.default()
        self.assertIn("audio", cfg.extensions)
        self.assertEqual(cfg.extensions["audio"].master_volume, 1.0)

        # Update works
        updated = cfg.with_updates(audio={"master_volume": 0.5})
        self.assertEqual(updated.extensions["audio"].master_volume, 0.5)

    def test_composition_at_game_level(self):
        # The ultimate net-new pattern: games compose EngineConfig into their own models.
        @dataclass(frozen=True, slots=True)
        class MyCustomSetting(DataModel):
            difficulty: str = "normal"
            version: int = 1

            def to_dict(self):
                return {"difficulty": self.difficulty, "version": self.version}

            @classmethod
            def from_dict(cls, data):
                return cls(**{k: data.get(k, v) for k, v in {"difficulty": "normal", "version": 1}.items()})

            def with_updates(self, **changes):
                return replace(self, **changes)

        @dataclass(frozen=True, slots=True)
        class MyGameConfig(DataModel):
            engine: EngineConfig
            custom: MyCustomSetting = field(default_factory=MyCustomSetting)
            version: int = 1

            def to_dict(self):
                return {
                    "engine": self.engine.to_dict(),
                    "custom": self.custom.to_dict(),
                    "version": self.version,
                }

            @classmethod
            def from_dict(cls, data):
                return cls(
                    engine=EngineConfig.from_dict(data.get("engine", {})),
                    custom=MyCustomSetting.from_dict(data.get("custom", {})),
                    version=data.get("version", 1),
                )

            def with_updates(self, **changes):
                return replace(self, **changes)

        game_cfg = MyGameConfig(engine=EngineConfig.default())
        self.assertIn("video", game_cfg.engine.extensions)
        self.assertEqual(game_cfg.custom.difficulty, "normal")


if __name__ == "__main__":
    unittest.main()