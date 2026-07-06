"""In-house GUI widget library for Grimoire3D.

Designed for video game tooling with these priorities:
- Tkinter-style grid layout (no manual pixel positions required)
- Correct behavior when widgets are deeply nested
- Works correctly with the engine's split-screen, virtual resolution,
  letterboxing, and resize handling
- Built directly on the Renderer so it shares the same batching and
  coordinate system as the rest of the game

Example:

    from grimoire3d.gui import GUIManager, Frame, Label, Button

    gui = GUIManager()
    root = Frame()
    gui.set_root(root)

    title = Label(root, text="My Tool")
    title.grid(row=0, column=0, columnspan=2, pady=8)

    btn = Button(root, text="Do Thing", command=do_something)
    btn.grid(row=1, column=0)

    # In your game loop:
    gui.layout(virtual_w, virtual_h)
    gui.handle_mouse(vx, vy, mouse_down)
    gui.handle_key_state()
    gui.draw(renderer)
"""

from __future__ import annotations

from .gui import GUIManager
from .widget import Widget
from .widgets import (
    Button,
    Checkbutton,
    Combobox,
    Entry,
    Frame,
    Label,
    Listbox,
    Menu,
    Menubutton,
    LabelFrame,
    PanedWindow,
    Progressbar,
    Notebook,
    Treeview,
    Separator,
    Sizegrip,
    Radiobutton,
    Scale,
    Scrollbar,
    Spinbox,
    Text,
    Canvas,
)

__all__ = [
    "GUIManager",
    "Widget",
    "Frame",
    "Label",
    "Button",
    "Entry",
    "Checkbutton",
    "Text",
    "Radiobutton",
    "Listbox",
    "Combobox",
    "Spinbox",
    "Scale",
    "Scrollbar",
    "Canvas",
    "Menu",
    "Menubutton",
    "LabelFrame",
    "PanedWindow",
    "Progressbar",
    "Notebook",
    "Treeview",
    "Separator",
    "Sizegrip",
]
