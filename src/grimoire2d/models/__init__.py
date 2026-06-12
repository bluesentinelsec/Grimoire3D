"""Models layer (data models).

Pure value objects and data containers (configs, world states, etc.).
No behavior, no side effects. See proposal 0001.

EngineConfig contains *only* an extensions dict (no hard-coded members).
All configuration, common or game-specific, is delivered via registered
DataModel extensions. This guarantees every addition is purely net-new code.

See models/base.py for the DataModel protocol.
Games define their own models and compose (see EngineConfig docstring).
"""

from . import title
from . import video
from . import timing

from .base import DataModel, register_extension
from .config import EngineConfig

# Re-export the individual models for convenience
from .title import TitleSetting
from .video import VideoSettings
from .timing import TimingSettings

__all__ = [
    "DataModel",
    "register_extension",
    "EngineConfig",
    "TitleSetting",
    "VideoSettings",
    "TimingSettings",
]