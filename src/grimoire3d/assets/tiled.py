"""Tiled JSON loader on top of the VFS.

Loads Tiled map exports (.json) and their associated tilesets as pure
Tiled* data models. All I/O goes through the VFS so we get directory
hot-reload and packed+obfuscated archives for free.

Usage (once we have a VFS instance):

    from grimoire3d.assets import load_tiled_map
    from grimoire3d.assets.vfs import VFS, DirProvider

    vfs = VFS()
    vfs.mount("assets/", DirProvider("assets"))

    tiled_map = load_tiled_map(vfs, "assets/screens/title.json")
    print(tiled_map.width, tiled_map.height)
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models.tiled import TiledMap
from .vfs import VirtualFileSystem


def load_tiled_map(vfs: VirtualFileSystem, path: str) -> TiledMap:
    """Load and parse a Tiled map JSON file through the VFS.

    The map may reference external tilesets and images; relative paths
    are resolved against the directory of the map file inside the VFS.
    (Current implementation loads the map JSON only; full tileset
    external resolution + image bytes loading comes in a follow-up.)
    """
    raw_bytes = vfs.read_bytes(path)
    data = json.loads(raw_bytes.decode("utf-8"))

    # Basic parse into our model (the from_dict already handles most structure)
    tiled_map = TiledMap.from_dict(data)

    # Store original path for later resolution of relative assets
    # (we can attach via properties or extend later)
    # For now we keep it in raw if needed by the caller.
    return tiled_map


def _resolve_relative(base_map_path: str, relative: str) -> str:
    """Resolve a tileset/image path relative to the map's directory."""
    base = Path(base_map_path).parent
    return (base / relative).as_posix()
