"""Models layer (data models).

Pure value objects and data containers (configs, world states, etc.).
No behavior, no side effects. See proposal 0001.

EngineConfig contains *only* an extensions dict (no hard-coded members).
All configuration, common or game-specific, is delivered via registered
DataModel extensions. This guarantees every addition is purely net-new code.

See models/base.py for the DataModel protocol.
Games define their own models and compose (see EngineConfig docstring).
"""

from . import title  # noqa: F401  (side-effect: registers extension)
from . import video  # noqa: F401
from . import timing  # noqa: F401
from . import lifecycle  # noqa: F401
from . import input  # noqa: F401
from . import app_state  # noqa: F401
from . import window_settings  # noqa: F401
from . import build_config  # noqa: F401
from . import virtual_resolution  # noqa: F401
from . import player  # noqa: F401
from . import input_frame  # noqa: F401
from . import multiplayer  # noqa: F401
from . import pause  # noqa: F401
from . import components  # noqa: F401
from . import actor  # noqa: F401
from . import scene  # noqa: F401
from . import scene_graph  # noqa: F401
from . import tiled  # noqa: F401  (side-effect + future re-exports)

from .base import DataModel, register_extension, register_component
from .config import EngineConfig
from .app_state import AppState

# Re-export the individual models for convenience
from .title import TitleSetting
from .video import VideoSettings
from .timing import TimingSettings
from .lifecycle import LifecycleState
from .input import InputState
from .window_settings import WindowSettings
from .build_config import BuildConfig
from .virtual_resolution import VirtualResolution
from .player import (
    PlayerIdentity,
    PlayerRoster,
    ROLE_LOCAL,
    ROLE_REMOTE,
    ROLE_AI,
    ROLE_REPLAY,
)
from .input_frame import InputFrame, InputBuffer
from .multiplayer import (
    MultiplayerConfig,
    ViewportAssignment,
    SimulationState,
    TOPOLOGY_SHARED_SCREEN,
    TOPOLOGY_SPLIT_SCREEN,
    TOPOLOGY_NETWORK_HOST,
    TOPOLOGY_NETWORK_CLIENT,
)
from .pause import (
    PauseState,
    GROUP_GAMEPLAY,
    GROUP_AUDIO,
    GROUP_UI,
    GROUP_INPUT,
)
from .components import TransformComponent, VelocityComponent
from .actor import Actor
from .scene import (
    Scene,
    SCENE_STATUS_LOADING,
    SCENE_STATUS_ACTIVE,
    SCENE_STATUS_PAUSED,
    SCENE_STATUS_CLOSING,
    SCENE_STATUS_CLOSED,
)
from .scene_graph import SceneGraph
from .tiled import (
    TiledMap,
    TiledLayer,
    TiledTileLayer,
    TiledObjectLayer,
    TiledObject,
    TiledTileset,
)

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
    "WindowSettings",
    "BuildConfig",
    "VirtualResolution",
    "PlayerIdentity",
    "PlayerRoster",
    "ROLE_LOCAL",
    "ROLE_REMOTE",
    "ROLE_AI",
    "ROLE_REPLAY",
    "InputFrame",
    "InputBuffer",
    "MultiplayerConfig",
    "ViewportAssignment",
    "SimulationState",
    "TOPOLOGY_SHARED_SCREEN",
    "TOPOLOGY_SPLIT_SCREEN",
    "TOPOLOGY_NETWORK_HOST",
    "TOPOLOGY_NETWORK_CLIENT",
    "PauseState",
    "GROUP_GAMEPLAY",
    "GROUP_AUDIO",
    "GROUP_UI",
    "GROUP_INPUT",
    "TransformComponent",
    "VelocityComponent",
    "Actor",
    "Scene",
    "SCENE_STATUS_LOADING",
    "SCENE_STATUS_ACTIVE",
    "SCENE_STATUS_PAUSED",
    "SCENE_STATUS_CLOSING",
    "SCENE_STATUS_CLOSED",
    "SceneGraph",
    "TiledMap",
    "TiledLayer",
    "TiledTileLayer",
    "TiledObjectLayer",
    "TiledObject",
    "TiledTileset",
    "register_component",
]
