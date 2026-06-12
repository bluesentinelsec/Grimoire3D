"""Models layer (data models).

Pure value objects and data containers (configs, world states, etc.).
No behavior, no side effects. See proposal 0001.

EngineConfig contains *only* an extensions dict (no hard-coded members).
All configuration, common or game-specific, is delivered via registered
DataModel extensions.

New core models for minimal app milestone (window + ESC to quit):
- LifecycleState: running / quit flags
- InputState: snapshot of pressed keys (for escape detection etc.)
- AppState: composed root (engine + lifecycle + input) + support for game-specific composition

See models/base.py for the DataModel protocol.
Games define their own models and compose (see AppState and EngineConfig docstrings).
"""

from . import title
from . import video
from . import timing
from . import lifecycle
from . import input
from . import app_state

from .base import DataModel, register_extension
from .config import EngineConfig
from .app_state import AppState

# Re-export the individual models for convenience
from .title import TitleSetting
from .video import VideoSettings
from .timing import TimingSettings
from .lifecycle import LifecycleState
from .input import InputState

__all__ = [
    "DataModel",
    "register_extension",
    "EngineConfig",
    "AppState",
    "TitleSetting",
    "VideoSettings",
    "TimingSettings",
    "LifecycleState",
    "InputState",
]