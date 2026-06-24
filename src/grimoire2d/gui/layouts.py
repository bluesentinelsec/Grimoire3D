"""Layout managers for the in-house GUI.

Currently focused on GridLayout to provide a Tkinter-grid-like experience.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .gui import GUIManager

if TYPE_CHECKING:
    from .widget import GridOptions, Widget


@dataclass
class GridCell:
    widget: "Widget"
    options: "GridOptions"


class GridLayout:
    """Grid layout manager (inspired by tkinter's grid).

    Usage:
        frame = Frame()
        label = Label(frame, text="Name")
        label.grid(row=0, column=0, sticky="w", padx=4)
        entry = Entry(frame)
        entry.grid(row=0, column=1, sticky="ew")

        frame.set_layout(GridLayout())
        # Later during GUI update:
        frame.layout.layout(frame.children, available_w, available_h)
    """

    def __init__(self) -> None:
        self.cells: list[GridCell] = []
        self.column_weights: dict[int, float] = {}
        self.row_weights: dict[int, float] = {}
        self._computed: bool = False

    def add(self, widget: "Widget", options: "GridOptions") -> None:
        self.cells.append(GridCell(widget, options))
        self._computed = False

    def set_column_weight(self, column: int, weight: float) -> None:
        self.column_weights[column] = max(0.0, weight)
        self._computed = False

    def set_row_weight(self, row: int, weight: float) -> None:
        self.row_weights[row] = max(0.0, weight)
        self._computed = False

    def layout(
        self,
        children: list["Widget"],
        avail_width: float,
        avail_height: float,
        gui: Optional["GUIManager"] = None,
    ) -> None:
        """Compute positions and sizes for all children that have grid options.

        This is a two-pass layout:
        1. Measure preferred sizes
        2. Distribute space according to weights and constraints
        """
        if not children:
            return

        # Collect only gridded children
        gridded: list[tuple[Widget, GridOptions]] = []
        for w in children:
            if w.grid_options is not None:
                gridded.append((w, w.grid_options))

        if not gridded:
            return

        # Find grid dimensions
        max_row = max((opt.row + opt.rowspan - 1) for _, opt in gridded)
        max_col = max((opt.column + opt.columnspan - 1) for _, opt in gridded)

        num_rows = max_row + 1
        num_cols = max_col + 1

        # Measure preferred sizes
        pref_widths: list[float] = [0.0] * num_cols
        pref_heights: list[float] = [0.0] * num_rows

        for widget, opt in gridded:
            pw, ph = widget.measure(gui)
            # Account for padding
            pw += opt.padx * 2 + opt.ipadx * 2
            ph += opt.pady * 2 + opt.ipady * 2

            # Spread across spanned cells (simple uniform for now)
            col_span = opt.columnspan
            row_span = opt.rowspan

            w_per_cell = pw / col_span if col_span > 0 else pw
            h_per_cell = ph / row_span if row_span > 0 else ph

            for c in range(opt.column, opt.column + col_span):
                pref_widths[c] = max(pref_widths[c], w_per_cell)
            for r in range(opt.row, opt.row + row_span):
                pref_heights[r] = max(pref_heights[r], h_per_cell)

        # Apply weights for extra space
        total_pref_w = sum(pref_widths)
        total_pref_h = sum(pref_heights)

        extra_w = max(0.0, avail_width - total_pref_w)
        extra_h = max(0.0, avail_height - total_pref_h)

        # Distribute extra space
        col_weights = [self.column_weights.get(c, 0.0) for c in range(num_cols)]
        row_weights = [self.row_weights.get(r, 0.0) for r in range(num_rows)]

        total_col_weight = sum(col_weights) or 1.0
        total_row_weight = sum(row_weights) or 1.0

        col_widths = [
            w
            + (
                extra_w * (col_weights[i] / total_col_weight)
                if total_col_weight > 0
                else 0
            )
            for i, w in enumerate(pref_widths)
        ]
        row_heights = [
            h
            + (
                extra_h * (row_weights[i] / total_row_weight)
                if total_row_weight > 0
                else 0
            )
            for i, h in enumerate(pref_heights)
        ]

        # Position widgets
        for widget, opt in gridded:
            x = sum(col_widths[: opt.column])
            y = sum(row_heights[: opt.row])

            cell_w = sum(col_widths[opt.column : opt.column + opt.columnspan])
            cell_h = sum(row_heights[opt.row : opt.row + opt.rowspan])

            # Apply external padding
            x += opt.padx
            y += opt.pady
            cell_w -= opt.padx * 2
            cell_h -= opt.pady * 2

            # Compute final size based on sticky
            w = min(widget.width or cell_w, cell_w)  # prefer measured or fill
            h = min(widget.height or cell_h, cell_h)

            sticky = opt.sticky.lower()
            if "e" in sticky and "w" in sticky:
                w = cell_w
            elif "e" in sticky:
                x = x + cell_w - w
            elif "w" not in sticky:
                x += (cell_w - w) / 2

            if "s" in sticky and "n" in sticky:
                h = cell_h
            elif "s" in sticky:
                y = y + cell_h - h
            elif "n" not in sticky:
                y += (cell_h - h) / 2

            # Apply internal padding
            widget.set_rect(
                x + opt.ipadx,
                y + opt.ipady,
                max(0.0, w - opt.ipadx * 2),
                max(0.0, h - opt.ipady * 2),
            )

        self._computed = True

    def get_preferred_size(
        self, children: list["Widget"], gui: Optional["GUIManager"] = None
    ) -> tuple[float, float]:
        """Compute preferred size based on measured children + padding."""
        if not children:
            return 0.0, 0.0

        gridded = [(w, w.grid_options) for w in children if w.grid_options]
        if not gridded:
            return 0.0, 0.0

        max_row = max((opt.row + opt.rowspan - 1) for _, opt in gridded)
        max_col = max((opt.column + opt.columnspan - 1) for _, opt in gridded)

        num_rows = max_row + 1
        num_cols = max_col + 1

        col_widths = [0.0] * num_cols
        row_heights = [0.0] * num_rows

        for widget, opt in gridded:
            pw, ph = widget.measure(gui)
            pw += opt.padx * 2 + opt.ipadx * 2
            ph += opt.pady * 2 + opt.ipady * 2

            col_span = opt.columnspan or 1
            row_span = opt.rowspan or 1
            w_per = pw / col_span
            h_per = ph / row_span

            for c in range(opt.column, opt.column + col_span):
                col_widths[c] = max(col_widths[c], w_per)
            for r in range(opt.row, opt.row + row_span):
                row_heights[r] = max(row_heights[r], h_per)

        total_w = sum(col_widths)
        total_h = sum(row_heights)
        # Add some margin
        return total_w + 10, total_h + 10
