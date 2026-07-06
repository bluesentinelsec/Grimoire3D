"""Assets and Virtual File System.

All asset loading in Grimoire3D **must** go through the VFS.

The `archive` submodule provides helpers to create and extract
(possibly obfuscated) zip-based archives.

Example::

    from grimoire3d.assets import archive
    from grimoire3d.assets.vfs import VFS, ZipProvider
    # or
    import grimoire3d.assets.vfs as vfs
"""

from __future__ import annotations

from . import archive, tiled, vfs
from .archive import create_archive, extract_archive
from .tiled import load_tiled_map
from .vfs import (
    DirProvider,
    MemoryProvider,
    VFS,
    VirtualFileSystem,
    ZipProvider,
)

__all__ = [
    "archive",
    "create_archive",
    "extract_archive",
    "tiled",
    "load_tiled_map",
    "vfs",
    "VFS",
    "VirtualFileSystem",
    "DirProvider",
    "ZipProvider",
    "MemoryProvider",
]
