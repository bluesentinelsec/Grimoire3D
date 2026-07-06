"""Tiled map data models (pure data, following the DataModel pattern).

These models represent the structure of a Tiled JSON export so that
screens, levels, and UI layouts can be authored entirely in Tiled and
loaded as data via the VFS.

Design notes:
- Only the subset we need for "compose games with data" is modelled.
- All types implement the DataModel protocol for serialization/hot-reload.
- Coordinates follow Tiled's default (pixels, origin top-left for objects
  in orthogonal maps; tile layers are row/col based).
- Custom properties are kept as raw dicts (games interpret them).
- No rendering or game logic lives here — pure data.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .base import DataModel


# ---------------------------------------------------------------------------
# Tileset
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TiledTileset(DataModel):
    """Reference to a tileset (embedded or external)."""

    first_gid: int
    name: str
    tile_width: int
    tile_height: int
    image: str | None = None  # path relative to the map or tileset file
    image_width: int | None = None
    image_height: int | None = None
    tile_count: int | None = None
    columns: int | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "first_gid": self.first_gid,
            "name": self.name,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "version": self.version,
        }
        if self.image:
            d["image"] = self.image
        if self.image_width is not None:
            d["image_width"] = self.image_width
        if self.image_height is not None:
            d["image_height"] = self.image_height
        if self.tile_count is not None:
            d["tile_count"] = self.tile_count
        if self.columns is not None:
            d["columns"] = self.columns
        if self.properties:
            d["properties"] = self.properties
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TiledTileset:
        return cls(
            first_gid=data.get("first_gid", 0),
            name=data.get("name", ""),
            tile_width=data.get("tile_width", 0),
            tile_height=data.get("tile_height", 0),
            image=data.get("image"),
            image_width=data.get("image_width"),
            image_height=data.get("image_height"),
            tile_count=data.get("tile_count"),
            columns=data.get("columns"),
            properties=data.get("properties", {}),
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> TiledTileset:
        return replace(self, **changes)


# ---------------------------------------------------------------------------
# Layer base + concrete types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TiledLayer(DataModel):
    """Base for all layer types."""

    id: int
    name: str
    type: str  # "tilelayer", "objectgroup", etc.
    visible: bool = True
    opacity: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    properties: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "visible": self.visible,
            "opacity": self.opacity,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "properties": self.properties,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TiledLayer:
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            type=data.get("type", ""),
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            offset_x=data.get("offset_x", 0.0),
            offset_y=data.get("offset_y", 0.0),
            properties=data.get("properties", {}),
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> TiledLayer:
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class TiledTileLayer(TiledLayer):
    """A tile layer (grid of tile GIDs)."""

    width: int = 0
    height: int = 0
    data: list[int] = field(default_factory=list)  # GIDs, row-major

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "width": self.width,
                "height": self.height,
                "data": self.data,
            }
        )
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TiledTileLayer:
        base = TiledLayer.from_dict(data)
        return cls(
            **{k: v for k, v in base.__dict__.items() if k != "type"},
            type="tilelayer",
            width=data.get("width", 0),
            height=data.get("height", 0),
            data=data.get("data", []),
        )

    def with_updates(self, **changes: Any) -> TiledTileLayer:
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class TiledObject(DataModel):
    """An individual object from an object layer."""

    id: int
    name: str = ""
    type: str = ""  # custom type e.g. "button", "enemy_spawn"
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0
    visible: bool = True
    gid: int | None = None  # if it's a tile object
    properties: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "visible": self.visible,
            "version": self.version,
        }
        if self.gid is not None:
            d["gid"] = self.gid
        if self.properties:
            d["properties"] = self.properties
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TiledObject:
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            type=data.get("type", ""),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 0.0),
            height=data.get("height", 0.0),
            rotation=data.get("rotation", 0.0),
            visible=data.get("visible", True),
            gid=data.get("gid"),
            properties=data.get("properties", {}),
            version=data.get("version", 1),
        )

    def with_updates(self, **changes: Any) -> TiledObject:
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class TiledObjectLayer(TiledLayer):
    """Object group layer."""

    objects: list[TiledObject] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["objects"] = [o.to_dict() for o in self.objects]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TiledObjectLayer:
        base = TiledLayer.from_dict(data)
        objs = [TiledObject.from_dict(o) for o in data.get("objects", [])]
        return cls(
            **{k: v for k, v in base.__dict__.items() if k != "type"},
            type="objectgroup",
            objects=objs,
        )

    def with_updates(self, **changes: Any) -> TiledObjectLayer:
        return replace(self, **changes)


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TiledMap(DataModel):
    """Top-level Tiled map data structure.

    This is the primary artifact loaded from a Tiled .json export and
    used to drive entire screens (splash, title, options, levels...).
    """

    version: str = "1.10"
    tiled_version: str = ""
    orientation: str = "orthogonal"
    render_order: str = "right-down"
    width: int = 0
    height: int = 0
    tile_width: int = 0
    tile_height: int = 0
    next_layer_id: int = 1
    next_object_id: int = 1
    layers: list[TiledLayer] = field(default_factory=list)
    tilesets: list[TiledTileset] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    # raw for anything we don't model yet
    raw: dict[str, Any] = field(default_factory=dict)
    map_version: int = 1  # our own versioning

    @property
    def pixel_width(self) -> int:
        return self.width * self.tile_width

    @property
    def pixel_height(self) -> int:
        return self.height * self.tile_height

    def get_layer(self, name: str) -> TiledLayer | None:
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def get_object_layers(self) -> list[TiledObjectLayer]:
        return [layer for layer in self.layers if isinstance(layer, TiledObjectLayer)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "tiled_version": self.tiled_version,
            "orientation": self.orientation,
            "render_order": self.render_order,
            "width": self.width,
            "height": self.height,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "next_layer_id": self.next_layer_id,
            "next_object_id": self.next_object_id,
            "layers": [layer.to_dict() for layer in self.layers],
            "tilesets": [t.to_dict() for t in self.tilesets],
            "properties": self.properties,
            "map_version": self.map_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TiledMap:
        layers: list[TiledLayer] = []
        for ld in data.get("layers", []):
            ltype = ld.get("type")
            if ltype == "tilelayer":
                layers.append(TiledTileLayer.from_dict(ld))
            elif ltype == "objectgroup":
                layers.append(TiledObjectLayer.from_dict(ld))
            else:
                layers.append(TiledLayer.from_dict(ld))

        tilesets = [TiledTileset.from_dict(ts) for ts in data.get("tilesets", [])]

        return cls(
            version=data.get("version", "1.10"),
            tiled_version=data.get("tiled_version", ""),
            orientation=data.get("orientation", "orthogonal"),
            render_order=data.get("render_order", "right-down"),
            width=data.get("width", 0),
            height=data.get("height", 0),
            tile_width=data.get("tilewidth", 0),
            tile_height=data.get("tileheight", 0),
            next_layer_id=data.get("nextlayerid", 1),
            next_object_id=data.get("nextobjectid", 1),
            layers=layers,
            tilesets=tilesets,
            properties=data.get("properties", {}),
            raw={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "version",
                    "tiledversion",
                    "orientation",
                    "renderorder",
                    "width",
                    "height",
                    "tilewidth",
                    "tileheight",
                    "nextlayerid",
                    "nextobjectid",
                    "layers",
                    "tilesets",
                    "properties",
                }
            },
            map_version=data.get("map_version", 1),
        )

    def with_updates(self, **changes: Any) -> TiledMap:
        return replace(self, **changes)


# Optional: register a component if people want to attach a full map to an actor
# (uncommon — usually the map drives multiple actors)
# register_component("tiled_map", TiledMap)  # usually not needed
