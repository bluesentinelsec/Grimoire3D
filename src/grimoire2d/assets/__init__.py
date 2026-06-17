"""Assets and Virtual File System.

All asset loading in Grimoire2D **must** go through the VFS.

Example::

    from grimoire2d.assets.vfs import VFS, DirProvider, ZipProvider
    # or
    import grimoire2d.assets.vfs as vfs
"""

from __future__ import annotations

from . import vfs
from .vfs import (
    DirProvider,
    MemoryProvider,
    VFS,
    VirtualFileSystem,
    ZipProvider,
)

__all__ = [
    "vfs",
    "VFS",
    "VirtualFileSystem",
    "DirProvider",
    "ZipProvider",
    "MemoryProvider",
]
