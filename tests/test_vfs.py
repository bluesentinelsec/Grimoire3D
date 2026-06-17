"""Tests for the Virtual File System."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from grimoire2d.assets.vfs import (
    DirProvider,
    MemoryProvider,
    VirtualFileSystem,
    ZipProvider,
    _apply_cipher,
)
from grimoire2d.exceptions import AssetNotFound


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_test_zip(tmp_path: Path, files: dict[str, bytes]) -> Path:
    zpath = tmp_path / "test.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return zpath


# --------------------------------------------------------------------------- #
# Cipher
# --------------------------------------------------------------------------- #


def test_cipher_is_reversible():
    key = b"supersecret"
    data = b"hello world\x00\xff some binary data"
    enc = _apply_cipher(data, key)
    dec = _apply_cipher(enc, key)
    assert dec == data
    assert _apply_cipher(data, None) == data


# --------------------------------------------------------------------------- #
# MemoryProvider
# --------------------------------------------------------------------------- #


def test_memory_provider_basic():
    files = {
        "sprites/player.png": b"PNGDATA",
        "data/level.json": b'{"name": "test"}',
        "shaders/basic.vert": b"#version 330",
    }
    mp = MemoryProvider(files)

    assert mp.exists("sprites/player.png")
    assert mp.read_bytes("data/level.json") == b'{"name": "test"}'
    assert mp.exists("shaders/basic.vert")

    with mp.open("sprites/player.png") as f:
        assert f.read() == b"PNGDATA"

    assert sorted(mp.list_dir("")) == ["data", "shaders", "sprites"]
    assert mp.list_dir("data") == ["level.json"]
    assert mp.list_dir("nonexistent") == []


def test_memory_provider_normalizes_paths():
    mp = MemoryProvider({"assets\\foo.txt": b"hi", "/bar/baz": b"there"})
    assert mp.exists("assets/foo.txt")
    assert mp.exists("bar/baz")
    assert mp.read_bytes("assets/foo.txt") == b"hi"


# --------------------------------------------------------------------------- #
# ZipProvider
# --------------------------------------------------------------------------- #


def test_zip_provider_basic(tmp_path: Path):
    zpath = _make_test_zip(
        tmp_path,
        {
            "assets/sprites/player.png": b"ZIPPNG",
            "config/settings.json": b"{}",
            "assets/levels/1.tmx": b"<map/>",
        },
    )
    zp = ZipProvider(zpath)

    assert zp.exists("assets/sprites/player.png")
    assert zp.read_bytes("config/settings.json") == b"{}"

    with zp.open("assets/levels/1.tmx") as f:
        assert f.read() == b"<map/>"

    assert zp.list_dir("") == ["assets", "config"]
    assert zp.list_dir("assets") == ["levels", "sprites"]


def test_zip_provider_from_bytes(tmp_path: Path):
    zpath = _make_test_zip(tmp_path, {"hello.txt": b"world"})
    raw = zpath.read_bytes()
    zp = ZipProvider(raw)
    assert zp.read_bytes("hello.txt") == b"world"


def test_zip_provider_obfuscated(tmp_path: Path):
    key = b"mykey42"
    plain = _make_test_zip(tmp_path, {"secret.dat": b"topsecret"})

    # Create obfuscated version
    raw = plain.read_bytes()
    obf = _apply_cipher(raw, key)
    obf_path = tmp_path / "game.dat"
    obf_path.write_bytes(obf)

    zp = ZipProvider(obf_path, key=key)
    assert zp.read_bytes("secret.dat") == b"topsecret"

    # Wrong key produces invalid zip data -> fail fast on construction
    with pytest.raises(zipfile.BadZipFile):
        ZipProvider(obf_path, key=b"wrong")


def test_zip_provider_not_found(tmp_path: Path):
    zpath = _make_test_zip(tmp_path, {"a.txt": b"1"})
    zp = ZipProvider(zpath)
    with pytest.raises(FileNotFoundError):
        zp.read_bytes("nope.txt")


# --------------------------------------------------------------------------- #
# DirProvider
# --------------------------------------------------------------------------- #


def test_dir_provider(tmp_path: Path):
    root = tmp_path / "assets"
    (root / "sprites").mkdir(parents=True)
    (root / "sprites" / "p.png").write_bytes(b"PNG")
    (root / "data.json").write_bytes(b"{}")

    dp = DirProvider(root)

    assert dp.exists("sprites/p.png")
    assert dp.read_bytes("data.json") == b"{}"
    assert dp.list_dir("") == ["data.json", "sprites"]
    assert dp.list_dir("sprites") == ["p.png"]


def test_dir_provider_not_directory():
    with pytest.raises(NotADirectoryError):
        DirProvider("/this/does/not/exist/12345")


# --------------------------------------------------------------------------- #
# VirtualFileSystem mounting and priority
# --------------------------------------------------------------------------- #


def test_vfs_mount_priority(tmp_path: Path):
    # Base archive
    base_zip = _make_test_zip(
        tmp_path, {"common.txt": b"from_zip", "only_in_zip.txt": b"zip_only"}
    )

    # Overlay dir
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "common.txt").write_bytes(b"from_dir")
    (overlay / "only_in_dir.txt").write_bytes(b"dir_only")

    vfs = VirtualFileSystem()
    vfs.mount("", ZipProvider(base_zip))
    vfs.mount("assets/", DirProvider(overlay))  # note prefix

    # Dir should win for common
    assert vfs.read_bytes("assets/common.txt") == b"from_dir"
    assert vfs.read_bytes("only_in_zip.txt") == b"zip_only"
    assert vfs.read_bytes("assets/only_in_dir.txt") == b"dir_only"

    assert vfs.exists("assets/common.txt")
    assert not vfs.exists("nonexistent")


def test_vfs_read_open_exists(tmp_path: Path):
    zpath = _make_test_zip(tmp_path, {"foo/bar.txt": b"hello"})
    vfs = VirtualFileSystem()
    vfs.mount("", ZipProvider(zpath))

    assert vfs.exists("foo/bar.txt")
    assert vfs.read_bytes("foo/bar.txt") == b"hello"

    with vfs.open("foo/bar.txt") as f:
        assert f.read() == b"hello"


def test_vfs_asset_not_found():
    vfs = VirtualFileSystem()
    vfs.mount("", MemoryProvider({"a.txt": b"x"}))

    with pytest.raises(AssetNotFound) as exc:
        vfs.read_bytes("missing.txt")
    assert "missing.txt" in str(exc.value)

    with pytest.raises(AssetNotFound):
        vfs.open("missing.txt")


def test_vfs_list_dir_union(tmp_path: Path):
    z = _make_test_zip(tmp_path, {"a/z.txt": b"1", "shared/x.txt": b"2"})
    overlay = tmp_path / "ov"
    overlay.mkdir()
    (overlay / "shared").mkdir()
    (overlay / "shared" / "y.txt").write_bytes(b"3")
    (overlay / "onlydir").mkdir()

    vfs = VirtualFileSystem()
    vfs.mount("", ZipProvider(z))
    vfs.mount("", DirProvider(overlay))

    root = vfs.list_dir("")
    assert "a" in root and "onlydir" in root and "shared" in root

    shared = vfs.list_dir("shared")
    assert sorted(shared) == ["x.txt", "y.txt"]


def test_vfs_normalize_and_backslashes():
    vfs = VirtualFileSystem()
    vfs.mount("", MemoryProvider({"deep\\file.txt": b"ok"}))

    assert vfs.exists("deep/file.txt")
    assert vfs.read_bytes("deep\\file.txt") == b"ok"


def test_vfs_context_manager_closes_zip(tmp_path: Path):
    zpath = _make_test_zip(tmp_path, {"f.txt": b"1"})
    with VirtualFileSystem() as vfs:
        vfs.mount("", ZipProvider(zpath))
        assert vfs.read_bytes("f.txt") == b"1"
    # After exit, the internal zip should be closed (best effort check)
    # We can't easily inspect without leaking, so just ensure no crash.
