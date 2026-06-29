"""Tiled-like level editor demo that exercises *all* implemented GUI widgets.

This is a visual/integration demo (not a full editor). Interactions provide
immediate visual feedback so it's obvious that each widget is working:

- Buttons, Checkbuttons, Radiobuttons, Menubuttons → change status / colors / log
- Entry / Text / Listbox / Combobox / Spinbox / Treeview → live updates + selection highlight
- Scale / Progressbar → value changes reflected in labels + bar fill
- Canvas (map + tileset) → painting tiles, swatches, grid toggle
- Notebook / LabelFrame / PanedWindow / Separator → structural layout + resizing
- Scrollbar → attached to scrollable Listbox/Text
- Sizegrip → bottom-right corner (drag updates status label)
- Menu (top + context) → menu items append to log, change map state

Layout is deliberately Tiled-inspired:
  top menubar + toolbar
  left tileset panel
  center map canvas (paintable)
  right tabbed inspector (layers / properties / hierarchy)
  bottom status + sizegrip

Run:
    python -m demos.gui_tiled_demo

Resize the window; the engine letterboxes the virtual surface (now 1:1 with display for crispness).
All widget positioning uses GridLayout (no hard-coded pixel positions for the widgets themselves).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pygame

from grimoire2d.presentation.window import GameWindow
from grimoire2d.gui import (
    GUIManager,
    Frame,
    Label,
    Button,
    Checkbutton,
    Radiobutton,
    Entry,
    Text,
    Listbox,
    Combobox,
    Spinbox,
    Scale,
    Scrollbar,
    Canvas,
    Menu,
    Menubutton,
    LabelFrame,
    PanedWindow,
    Progressbar,
    Notebook,
    Treeview,
    Separator,
    Sizegrip,
)


# ---------------------------------------------------------------------------
# Demo state (fake "business" data for visual feedback only)
# ---------------------------------------------------------------------------


class DemoState:
    def __init__(self) -> None:
        self.status = "Ready — click widgets to see feedback"
        self.map_name = "untitled.tmx"
        self.current_tool = "Pen"
        self.current_color = (0.2, 0.7, 0.3, 1.0)
        self.brush_size = 16
        self.show_grid = True
        self.snap = True
        self.opacity = 1.0
        self.selected_layer = 0
        self.layers = ["Background", "Terrain", "Objects", "UI"]
        self.placed_tiles: list[dict[str, Any]] = []  # {'x':, 'y':, 'color':, 'size':}
        self.log_lines: list[str] = ["Demo started"]
        self.progress = 0.0
        self.progress_running = False
        self.tileset_selection = 0
        self.tree_selection = ""

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
        if len(self.log_lines) > 12:
            self.log_lines.pop(0)

    def paint_tile(self, cx: float, cy: float) -> None:
        size = self.brush_size
        col = self.current_color
        self.placed_tiles.append({"x": cx, "y": cy, "color": col, "size": size})
        self.log(f"Painted tile at ({int(cx)}, {int(cy)}) size={size}")

    def clear_map(self) -> None:
        self.placed_tiles.clear()
        self.log("Map cleared")

    def add_layer(self) -> None:
        name = f"Layer{len(self.layers) + 1}"
        self.layers.append(name)
        self.log(f"Added {name}")

    def toggle_grid(self) -> None:
        self.show_grid = not self.show_grid
        self.log(f"Grid {'on' if self.show_grid else 'off'}")

    def set_tool(self, tool: str) -> None:
        self.current_tool = tool
        # visual hint via color
        if tool == "Pen":
            self.current_color = (0.2, 0.7, 0.3, 1.0)
        elif tool == "Eraser":
            self.current_color = (0.7, 0.2, 0.2, 1.0)
        elif tool == "Select":
            self.current_color = (0.3, 0.5, 0.9, 1.0)
        self.log(f"Tool: {tool}")


state = DemoState()


# ---------------------------------------------------------------------------
# Menu builders
# ---------------------------------------------------------------------------


def build_file_menu() -> Menu:
    m = Menu()
    m.add_command("New Map", command=lambda: _menu_action("New Map"))
    m.add_command("Open...", command=lambda: _menu_action("Open"))
    m.add_command("Save", command=lambda: _menu_action("Save"))
    m.add_separator()
    m.add_command("Export PNG", command=lambda: _start_fake_export())
    m.add_command("Quit", command=lambda: _menu_action("Quit (demo)"))
    return m


def build_edit_menu() -> Menu:
    m = Menu()
    m.add_command("Undo", command=lambda: _menu_action("Undo"))
    m.add_command("Redo", command=lambda: _menu_action("Redo"))
    m.add_separator()
    m.add_command("Clear Map", command=lambda: state.clear_map())
    return m


def build_view_menu() -> Menu:
    m = Menu()
    # Real toggles (our Menu implements add_command)
    m.add_command("Toggle Grid", command=state.toggle_grid)
    m.add_command("Toggle Snap", command=_toggle_snap)
    return m


def build_layer_menu() -> Menu:
    m = Menu()
    m.add_command("New Layer", command=lambda: state.add_layer())
    m.add_command("Duplicate Layer", command=lambda: _menu_action("Duplicate Layer"))
    m.add_separator()
    m.add_command("Delete Layer", command=lambda: _menu_action("Delete Layer"))
    return m


def _menu_action(msg: str) -> None:
    state.log(msg)
    state.status = msg


def _toggle_snap() -> None:
    state.snap = not state.snap
    state.log(f"Snap {'on' if state.snap else 'off'}")


def _start_fake_export() -> None:
    state.progress = 0.0
    state.progress_running = True
    state.log("Starting export...")


# ---------------------------------------------------------------------------
# Custom Map Canvas (exercises Canvas + painting)
# ---------------------------------------------------------------------------


class MapCanvas(Canvas):
    """Canvas that acts as the editable map view."""

    def __init__(self, parent: Optional[Frame] = None, **kwargs: Any) -> None:
        super().__init__(
            parent, width=620, height=480, bg=(0.25, 0.25, 0.28, 1.0), **kwargs
        )
        self.grid_items: list[int] = []

    def _ensure_grid(self) -> None:
        # Recreate grid lines when toggled
        for iid in self.grid_items:
            self.delete(iid)
        self.grid_items.clear()
        if not state.show_grid:
            return
        step = 32
        w, h = 620, 480
        for x in range(0, w + 1, step):
            iid = self.create_line(x, 0, x, h, fill=(0.35, 0.35, 0.4, 1.0))
            self.grid_items.append(iid)
        for y in range(0, h + 1, step):
            iid = self.create_line(0, y, w, y, fill=(0.35, 0.35, 0.4, 1.0))
            self.grid_items.append(iid)

    def on_mouse_press(self, x: float, y: float, button: int) -> bool:
        # Let base Canvas do its thing (item dispatch etc.)
        super().on_mouse_press(x, y, button)

        if button == 1:  # left paint
            cx = self.canvasx(x)
            cy = self.canvasy(y)
            if state.snap:
                step = 32
                cx = round(cx / step) * step
                cy = round(cy / step) * step
            state.paint_tile(cx, cy)
            size = state.brush_size
            col = state.current_color
            self.create_rectangle(
                cx - size / 2,
                cy - size / 2,
                cx + size / 2,
                cy + size / 2,
                fill=col,
            )
            return True
        elif button == 3:  # right click → visual "context" indication
            state.log("Context menu (right-click) at map location")
            # Visual indication: place a small marker
            cx = self.canvasx(x)
            cy = self.canvasy(y)
            self.create_oval(
                cx - 6, cy - 6, cx + 6, cy + 6, outline=(1, 0.8, 0, 1), width=2
            )
            return True
        return False


# ---------------------------------------------------------------------------
# UI construction
# ---------------------------------------------------------------------------


def build_ui(gui: GUIManager) -> MapCanvas:
    root = Frame()
    gui.set_root(root)
    root.grid_rowconfigure(0, weight=0)  # menu
    root.grid_rowconfigure(1, weight=0)  # toolbar
    root.grid_rowconfigure(2, weight=1)  # main content
    root.grid_rowconfigure(3, weight=0)  # status
    root.grid_columnconfigure(0, weight=1)

    # --- Menubar (exercises Menubutton + Menu) ---
    menubar = Frame(root)
    menubar.grid(row=0, column=0, sticky="ew")
    menubar.grid_columnconfigure(99, weight=1)  # spacer

    file_mb = Menubutton(menubar, text="File", menu=build_file_menu())
    file_mb.grid(row=0, column=0, padx=2)
    edit_mb = Menubutton(menubar, text="Edit", menu=build_edit_menu())
    edit_mb.grid(row=0, column=1, padx=2)
    view_mb = Menubutton(menubar, text="View", menu=build_view_menu())
    view_mb.grid(row=0, column=2, padx=2)
    layer_mb = Menubutton(menubar, text="Layer", menu=build_layer_menu())
    layer_mb.grid(row=0, column=3, padx=2)
    help_mb = Menubutton(menubar, text="Help")
    help_mb.grid(row=0, column=4, padx=2)

    # --- Toolbar (mix of many widgets) ---
    toolbar = Frame(root)
    toolbar.grid(row=1, column=0, sticky="ew")
    col = 0

    Button(toolbar, text="New", command=lambda: _menu_action("New")).grid(
        row=0, column=col, padx=2
    )
    col += 1
    Button(toolbar, text="Save", command=lambda: _menu_action("Save")).grid(
        row=0, column=col, padx=2
    )
    col += 1
    Button(toolbar, text="Clear Map", command=state.clear_map).grid(
        row=0, column=col, padx=2
    )
    col += 1

    Separator(toolbar, orient="vertical").grid(row=0, column=col, padx=4, sticky="ns")
    col += 1

    Checkbutton(
        toolbar, text="Grid", variable=[state.show_grid], command=state.toggle_grid
    ).grid(row=0, column=col, padx=2)
    col += 1
    Checkbutton(toolbar, text="Snap", variable=[state.snap], command=_toggle_snap).grid(
        row=0, column=col, padx=2
    )
    col += 1

    Separator(toolbar, orient="vertical").grid(row=0, column=col, padx=4, sticky="ns")
    col += 1

    # Radio tools
    for tool in ("Pen", "Eraser", "Select"):
        Radiobutton(
            toolbar,
            text=tool,
            variable=[state.current_tool],
            value=tool,
            command=lambda t=tool: state.set_tool(t),
        ).grid(row=0, column=col, padx=1)
        col += 1

    Separator(toolbar, orient="vertical").grid(row=0, column=col, padx=4, sticky="ns")
    col += 1

    Label(toolbar, text="Brush:").grid(row=0, column=col, padx=2)
    col += 1
    Spinbox(toolbar, width=4, from_=4, to=64, increment=2).grid(
        row=0, column=col, padx=2
    )
    col += 1

    Label(toolbar, text="Size:").grid(row=0, column=col, padx=2)
    col += 1
    scale = Scale(
        toolbar,
        from_=4,
        to=64,
        length=80,
        showvalue=False,
        command=lambda v: setattr(state, "brush_size", int(v)),
    )
    scale.grid(row=0, column=col, padx=2)
    col += 1

    Label(toolbar, text="Opacity:").grid(row=0, column=col, padx=2)
    col += 1
    op_scale = Scale(
        toolbar,
        from_=0.0,
        to=1.0,
        length=60,
        resolution=0.1,
        command=lambda v: setattr(state, "opacity", float(v)),
    )
    op_scale.grid(row=0, column=col, padx=2)
    col += 1

    Combobox(
        toolbar, values=["Orthogonal", "Isometric", "Hex"], width=10, state="readonly"
    ).grid(row=0, column=col, padx=2)
    col += 1

    # --- Main area: PanedWindow (left | center | right) ---
    main_split = PanedWindow(root, orient="horizontal")
    main_split.grid(row=2, column=0, sticky="nsew")

    # LEFT: Tileset
    left = LabelFrame(main_split, text="Tileset")
    main_split.add(left)
    left.grid_rowconfigure(0, weight=1)
    left.grid_columnconfigure(0, weight=1)

    tileset_canvas = Canvas(left, width=160, height=140, bg=(0.15, 0.15, 0.18, 1.0))
    tileset_canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
    # Fake tileset swatches
    for i in range(4):
        for j in range(3):
            colr = (0.3 + i * 0.15, 0.4 + j * 0.1, 0.5, 1.0)
            tileset_canvas.create_rectangle(
                8 + j * 48, 8 + i * 36, 8 + j * 48 + 40, 8 + i * 36 + 28, fill=colr
            )

    tiles_lb = Listbox(
        left, items=["Grass", "Stone", "Water", "Tree", "Wall"], height=5
    )
    tiles_lb.grid(row=1, column=0, sticky="ew", padx=4)
    tiles_sb = Scrollbar(left, orient="vertical", command=tiles_lb.yview)
    tiles_lb.yscrollcommand = tiles_sb.set
    tiles_sb.grid(row=1, column=1, sticky="ns")

    # CENTER: Map
    center = LabelFrame(main_split, text="Map View (click to paint)")
    main_split.add(center)
    center.grid_rowconfigure(0, weight=1)
    center.grid_columnconfigure(0, weight=1)

    map_canvas = MapCanvas(center)
    map_canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
    # initial grid + a few demo tiles
    map_canvas._ensure_grid()
    for i in range(3):
        map_canvas.create_rectangle(
            64 + i * 80, 96, 96 + i * 80, 128, fill=(0.4 + i * 0.1, 0.6, 0.3, 1.0)
        )

    # RIGHT: Notebook with different widgets
    right = LabelFrame(main_split, text="Inspector")
    main_split.add(right)

    nb = Notebook(right)
    nb.grid(row=0, column=0, sticky="nsew")
    right.grid_rowconfigure(0, weight=1)
    right.grid_columnconfigure(0, weight=1)

    # --- Notebook Tab 1: Layers (Listbox + buttons + scrollbar) ---
    layers_tab = Frame(nb)
    nb.add(layers_tab, text="Layers")
    layers_tab.grid_rowconfigure(0, weight=1)
    layers_tab.grid_columnconfigure(0, weight=1)

    layers_lb = Listbox(layers_tab, items=state.layers, height=8, selectmode="single")
    layers_lb.grid(row=0, column=0, sticky="nsew")
    layers_sb = Scrollbar(layers_tab, orient="vertical", command=layers_lb.yview)
    layers_lb.yscrollcommand = layers_sb.set
    layers_sb.grid(row=0, column=1, sticky="ns")

    def on_layer_select():
        if layers_lb.selected:
            state.selected_layer = layers_lb.selected[0]
            state.log(f"Selected layer {state.layers[state.selected_layer]}")

    # Note: we poll in update_ui for simplicity

    Button(layers_tab, text="Add Layer", command=state.add_layer).grid(
        row=1, column=0, pady=2
    )
    Button(
        layers_tab, text="Delete", command=lambda: state.log("Delete layer (fake)")
    ).grid(row=2, column=0, pady=2)

    # --- Notebook Tab 2: Properties (many widgets) ---
    props_tab = LabelFrame(nb, text="Properties")
    nb.add(props_tab, text="Properties")
    props_tab.grid_columnconfigure(1, weight=1)

    row = 0
    Label(props_tab, text="Name:").grid(row=row, column=0, sticky="w", padx=4)
    name_entry = Entry(props_tab, text=state.map_name)
    name_entry.grid(row=row, column=1, sticky="ew", padx=4)
    row += 1

    Label(props_tab, text="Opacity:").grid(row=row, column=0, sticky="w", padx=4)
    op_lbl = Label(props_tab, text=f"{state.opacity:.1f}")
    op_lbl.grid(row=row, column=1, sticky="w")
    Scale(
        props_tab,
        from_=0.0,
        to=1.0,
        length=120,
        resolution=0.1,
        command=lambda v: (
            setattr(state, "opacity", float(v)),
            setattr(op_lbl, "text", f"{float(v):.1f}"),
        ),
    ).grid(row=row, column=2, padx=4)
    row += 1

    Checkbutton(props_tab, text="Visible", variable=[True]).grid(
        row=row, column=0, columnspan=2, sticky="w", padx=4
    )
    row += 1

    Label(props_tab, text="Blend:").grid(row=row, column=0, sticky="w", padx=4)
    Combobox(props_tab, values=["Normal", "Add", "Multiply", "Overlay"], width=10).grid(
        row=row, column=1, sticky="w"
    )
    row += 1

    Label(props_tab, text="Z-Order:").grid(row=row, column=0, sticky="w", padx=4)
    Spinbox(props_tab, from_=0, to=100, width=5).grid(row=row, column=1, sticky="w")
    row += 1

    Label(props_tab, text="Notes:").grid(row=row, column=0, sticky="nw", padx=4)
    notes = Text(props_tab, height=4)
    notes.grid(row=row, column=1, columnspan=2, sticky="ew")
    notes.insert(0, "Editable multi-line text widget.\nTry typing here!")
    row += 1

    pb = Progressbar(props_tab, length=160)
    pb.grid(row=row, column=0, columnspan=2, pady=4)
    Button(props_tab, text="Simulate Export", command=_start_fake_export).grid(
        row=row, column=2
    )

    # --- Notebook Tab 3: Scene Tree ---
    tree_tab = Frame(nb)
    nb.add(tree_tab, text="Scene")
    tree_tab.grid_rowconfigure(0, weight=1)
    tree_tab.grid_columnconfigure(0, weight=1)

    tree = Treeview(tree_tab, columns=("type", "id"), height=8)
    tree.grid(row=0, column=0, sticky="nsew")
    tree.insert("", text="Map Root", values=("group", "0"), open=True)
    tree.insert("I1", text="Layer: Background", values=("layer", "1"))
    tree.insert("I1", text="Layer: Objects", values=("layer", "2"), open=True)
    tree.insert("I3", text="Player", values=("sprite", "42"))
    tree.insert("I3", text="Enemy Spawner", values=("object", "99"))
    tree.yscrollcommand = None  # could attach scrollbar

    # --- Bottom status bar ---
    status_bar = Frame(root)
    status_bar.grid(row=3, column=0, sticky="ew")
    status_bar.grid_columnconfigure(0, weight=1)

    status_lbl = Label(status_bar, text=state.status)
    status_lbl.grid(row=0, column=0, sticky="w", padx=6)

    Separator(status_bar, orient="vertical").grid(row=0, column=1, sticky="ns", padx=4)

    # Live value from scale example
    live_lbl = Label(status_bar, text=f"Brush: {state.brush_size}")
    live_lbl.grid(row=0, column=2, padx=6)

    Sizegrip(status_bar).grid(row=0, column=3, sticky="se")

    # Store references for update loop
    ui_refs = {
        "status_lbl": status_lbl,
        "live_lbl": live_lbl,
        "name_entry": name_entry,
        "layers_lb": layers_lb,
        "tiles_lb": tiles_lb,
        "progress": pb,
        "map_canvas": map_canvas,
        "tree": tree,
        "notebook": nb,
        "op_lbl": op_lbl,
    }
    return map_canvas, ui_refs


def _update_ui(ui_refs: dict[str, Any]) -> None:
    """Poll a few widgets and push state so things look alive."""
    # status
    ui_refs["status_lbl"].text = state.status

    # live brush
    ui_refs[
        "live_lbl"
    ].text = f"Brush: {state.brush_size}  Opacity: {state.opacity:.1f}"

    # sync entry <-> state (simple poll)
    if ui_refs["name_entry"].get() != state.map_name:
        state.map_name = ui_refs["name_entry"].get()
        state.log(f"Map name → {state.map_name}")

    # layers list (reflect additions)
    if ui_refs["layers_lb"].items != state.layers:
        ui_refs["layers_lb"].items = state.layers[:]

    # tiles list selection drives color hint
    if ui_refs["tiles_lb"].selected:
        idx = ui_refs["tiles_lb"].selected[0]
        colors = [
            (0.2, 0.7, 0.3, 1),
            (0.6, 0.4, 0.2, 1),
            (0.2, 0.5, 0.9, 1),
            (0.8, 0.2, 0.2, 1),
            (0.9, 0.9, 0.3, 1),
        ]
        state.current_color = colors[idx % len(colors)]

    # fake progress animation
    if state.progress_running:
        state.progress = min(1.0, state.progress + 0.02)
        ui_refs["progress"].set(state.progress * 100)
        if state.progress >= 1.0:
            state.progress_running = False
            state.log("Export complete (fake)")
            ui_refs["progress"].set(0)

    # sync map grid visibility
    if ui_refs["map_canvas"].grid_items or not state.show_grid:
        ui_refs["map_canvas"]._ensure_grid()

    # tree selection feedback
    if ui_refs["tree"].selection():
        sel = ui_refs["tree"].selection()[0]
        if sel != state.tree_selection:
            state.tree_selection = sel
            state.log(f"Tree selected: {sel}")

    # notebook tab doesn't need much, just being there exercises it


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    print("Grimoire2D GUI Widgets Demo — Tiled-style editor")
    print(
        "Exercise every widget. Watch for highlights, live updates, paints, menus, drags, etc."
    )
    print("Left-click map to paint. Right-click map for context menu.")
    print("Drag PanedWindow sashes. Use Sizegrip. Type in entries. Toggle checks, etc.")
    print("ESC to quit.")

    # Use the user's display resolution for 1:1 virtual-to-physical mapping.
    # This avoids scaling/letterbox blur and gives crisp output.
    VIRTUAL_WIDTH = 1728
    VIRTUAL_HEIGHT = 1117

    # Load a high-quality embedded font (Source Serif 4).
    # Loading bytes means the data can come from VFS (vfs.read_bytes(...))
    # or be truly embedded (e.g. via package_data + importlib.resources).
    # This path is for the local experiment; in a real game you'd package it.
    font_bytes = None
    font_candidates = [
        "/Users/michaellong/Downloads/DM_Sans,EB_Garamond,IBM_Plex_Sans,Inter,Merriweather,etc-3/Source_Serif_4/static/SourceSerif4_18pt-Regular.ttf",
        "/Users/michaellong/Downloads/DM_Sans,EB_Garamond,IBM_Plex_Sans,Inter,Merriweather,etc-3/Source_Serif_4/static/SourceSerif4_36pt-Regular.ttf",
    ]
    for fp in font_candidates:
        try:
            with open(fp, "rb") as f:
                font_bytes = f.read()
            print(f"Loaded custom font from {fp}")
            break
        except OSError:
            continue
    if font_bytes is None:
        print(
            "Warning: custom font not found at expected path; falling back to default (may look blurry)."
        )

    win = GameWindow(
        "Grimoire2D — Tiled-like GUI Demo (all widgets)",
        virtual_width=VIRTUAL_WIDTH,
        virtual_height=VIRTUAL_HEIGHT,
        font_bytes=font_bytes,
    )
    r = win.renderer

    gui = GUIManager()
    map_canvas, ui_refs = build_ui(gui)

    # initial grid refresh
    map_canvas._ensure_grid()

    while win.is_open:
        for event in win.poll():
            if event.type == pygame.QUIT:
                win.close()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                win.close()
            else:
                gui.handle_event(event)

        # Mouse in virtual space
        mx, my = pygame.mouse.get_pos()
        vx, vy = win.screen_to_virtual(mx, my)
        mouse_pressed = bool(pygame.mouse.get_pressed()[0])
        gui.handle_mouse(vx, vy, mouse_pressed)

        # Buffered key state for responsive held-key editing (backspace, arrows, etc.)
        gui.handle_key_state()

        win.begin_frame()

        # Background
        r.draw_rect(0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT, (0.12, 0.12, 0.14, 1.0))

        # Drive the GUI
        gui.layout(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, r)
        gui.draw(r)

        # Update live state / labels / fake animation
        _update_ui(ui_refs)

        # Tiny overlay hint (not a widget)
        r.draw_text(
            f"Status: {state.status}   |   Tool: {state.current_tool}   |   Tiles: {len(state.placed_tiles)}",
            20,
            VIRTUAL_HEIGHT - 20,
            color=(0.7, 0.7, 0.75, 1.0),
            font_size=14,
        )

        win.end_frame()

    win.quit()


if __name__ == "__main__":
    main()
