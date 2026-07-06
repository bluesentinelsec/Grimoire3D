"""EngineConfig - the top-level container for engine configuration.

This file contains *only* EngineConfig. All actual configuration data
lives in separate model files (title.py, video.py, timing.py, etc.) and
is registered via the mechanism in base.py.

This design ensures that EngineConfig itself is closed for modification.
Every addition of a new configuration category is purely net-new code.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .base import DataModel, register_extension  # register_extension is re-exported for convenience


@dataclass(frozen=True, slots=True)
class EngineConfig(DataModel):
    """Pure container for engine configuration via extensions only.

    **This class has ZERO hard-coded configuration members.**

    It contains only:
    - version
    - extensions: dict[str, DataModel]

    ALL settings — common engine ones (title, video, timing, ...) and any
    game-specific ones — live exclusively as named entries in the extensions dict.

    This is the strongest possible application of the Open/Closed Principle
    for this model:
    - The structure of EngineConfig is closed forever.
    - Every single addition (new audio settings, new accessibility category,
      game-specific difficulty, whatever) is purely net-new code.
    - No PR modifying this file is ever required to add functionality.

    How to add a new category (100% net-new):
    1. Create a new dataclass (e.g. in a new file audio.py) that implements DataModel.
    2. At the bottom of that file: register_extension("audio", AudioSettings)
    3. Use it: cfg = EngineConfig.default(); cfg.extensions["audio"]...
       Or better, compose at game level (see below).

    Recommended access for known categories:
        cfg.extensions["video"].width
        cfg.extensions["title"].value

    For maximum net-new PRs in actual games, always wrap:
        @dataclass(frozen=True, slots=True)
        class MyGameConfig(DataModel):
            engine: EngineConfig
            audio: AudioSettings
            my_difficulty: MyDifficultySetting
            ...

    Use EngineConfig.default() to get a baseline with all registered categories.

    See models/base.py for the full DataModel contract.
    """

    version: int = 1
    extensions: dict[str, DataModel] = field(default_factory=dict)

    @classmethod
    def default(cls) -> EngineConfig:
        """Create with all registered defaults populated.

        This is the recommended way to get a baseline EngineConfig.
        New registrations (in other modules) will automatically be picked up
        when this is called (as long as the module is imported).
        """
        from .base import _settings_registry  # internal but necessary here

        exts = {name: model_cls() for name, model_cls in _settings_registry.items()}
        return cls(extensions=exts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (for VFS/persistence boundary)."""
        return {
            "version": self.version,
            "extensions": {k: v.to_dict() for k, v in self.extensions.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EngineConfig:
        """Deserialize from a plain dict.

        Uses the registry to reconstruct known extensions.
        Unknown extensions are left as raw dicts (callers can handle).
        """
        from .base import _settings_registry

        ext_data = data.get("extensions", {})
        extensions = {}
        for k, v in ext_data.items():
            if k in _settings_registry:
                extensions[k] = _settings_registry[k].from_dict(v)
            else:
                extensions[k] = v  # raw for unknown / game-specific
        return cls(
            version=data.get("version", 1),
            extensions=extensions,
        )

    def with_updates(self, **changes: Any) -> EngineConfig:
        """Return a new EngineConfig with updates applied inside extensions.

        Supports nested: with_updates(video={"width": 1280}, title={"value": "New"})
        Also supports direct extensions update.
        """
        new_ext = dict(self.extensions)
        if "extensions" in changes:
            new_ext.update(changes["extensions"])
        for key, value in changes.items():
            if key != "extensions" and key in new_ext and isinstance(new_ext[key], DataModel):
                new_ext[key] = new_ext[key].with_updates(**value)
            elif key != "extensions":
                # allow adding new extensions this way
                new_ext[key] = value
        return replace(self, extensions=new_ext)