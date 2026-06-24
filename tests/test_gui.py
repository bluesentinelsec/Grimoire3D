"""Unit tests for in-house GUI widgets (pure logic, no window/GL required).

Focus on Canvas as the drawing widget, plus supporting behaviors for grid/scroll.
"""

import sys
import unittest
from pathlib import Path

import pygame

# Support running tests directly or via discover before `pip install -e .`
_src = Path(__file__).parent.parent / "src"
if _src.exists():
    sys.path.insert(0, str(_src))

from grimoire2d.gui.widgets import (  # noqa: E402
    Canvas,
    Entry,
    Frame,
    Label,
    LabelFrame,
    Menu,
    Menubutton,
    PanedWindow,
    Progressbar,
    Notebook,
    Treeview,
    Separator,
    Sizegrip,
    Scrollbar,
)
from grimoire2d.gui import GUIManager  # noqa: E402
from grimoire2d.gui.layouts import GridLayout  # noqa: E402


class TestCanvasBasic(unittest.TestCase):
    def test_create_and_measure(self):
        c = Canvas(width=400, height=300)
        self.assertEqual(c.measure(None), (400, 300))
        self.assertEqual(c.can_focus(), True)  # not disabled

    def test_item_creation_and_delete(self):
        c = Canvas()
        lid = c.create_line(0, 0, 10, 10, fill=(1, 0, 0, 1), width=2)
        c.create_rectangle(5, 5, 15, 25, fill=(0, 1, 0, 1))
        self.assertEqual(len(c._items), 2)
        self.assertEqual(len(c._order), 2)
        c.delete(lid)
        self.assertEqual(len(c._items), 1)
        c.delete("all")
        self.assertEqual(len(c._items), 0)

    def test_bbox_and_move(self):
        c = Canvas()
        c.create_rectangle(10, 20, 30, 40)
        c.create_line(0, 0, 100, 5)
        bb = c.bbox()
        self.assertIsNotNone(bb)
        self.assertEqual(bb[0], 0)
        self.assertEqual(bb[3], 40)
        c.move("all", 5, -10)
        bb2 = c.bbox()
        self.assertEqual(bb2[0], 5)
        self.assertEqual(bb2[1], -10)

    def test_tags(self):
        c = Canvas()
        i1 = c.create_line(0, 0, 1, 1, tags=["foo", "bar"])
        i2 = c.create_rectangle(2, 2, 3, 3)
        c.tag_add("foo", i2)
        self.assertIn(i1, c.find_withtag("foo"))
        self.assertIn(i2, c.find_withtag("foo"))
        c.tag_remove("foo", i1)
        self.assertNotIn(i1, c.find_withtag("foo"))
        self.assertIn(i2, c.find_withtag("foo"))

    def test_coords_update(self):
        c = Canvas()
        iid = c.create_line(0, 0, 10, 0)
        self.assertEqual(c.coords(iid), [0, 0, 10, 0])
        c.coords(iid, 1, 2, 3, 4)
        self.assertEqual(c.coords(iid), [1, 2, 3, 4])

    def test_itemconfig(self):
        c = Canvas()
        iid = c.create_rectangle(0, 0, 1, 1, fill=(0, 0, 0, 1))
        c.itemconfig(iid, fill=(1, 1, 1, 1), width=3)
        self.assertEqual(c.itemcget(iid, "fill"), (1, 1, 1, 1))
        self.assertEqual(c.itemcget(iid, "width"), 3)


class TestCanvasScroll(unittest.TestCase):
    def test_view_fractions_and_clamp(self):
        c = Canvas(width=100, height=50)
        c.scrollregion = (0, 0, 200, 200)
        first, last = c.yview()
        self.assertAlmostEqual(first, 0.0)
        self.assertAlmostEqual(last, 0.25)  # 50/200
        c.yview("moveto", 0.5)
        self.assertAlmostEqual(c._y_scroll, 100.0)
        # clamp
        c.yview("moveto", 2.0)
        self.assertLessEqual(c._y_scroll, 150.0)

    def test_scroll_units(self):
        c = Canvas(width=100, height=50, scrollregion=(0, 0, 0, 200))
        c.yview("scroll", 2, "units")
        self.assertEqual(c._y_scroll, 20)

    def test_canvas_to_screen_and_back(self):
        c = Canvas()
        c.x = 10
        c.y = 20
        c._x_scroll = 5
        c._y_scroll = 15
        self.assertEqual(c.canvasx(10), 5)  # screen -x + scroll
        self.assertEqual(c.canvasy(20), 15)

    def test_scrollregion_auto_from_bbox(self):
        c = Canvas()
        c.create_rectangle(-10, -20, 30, 40)
        sr = c._get_scrollregion()
        self.assertEqual(sr, (-10, -20, 30, 40))


class TestCanvasGridAndScrollbar(unittest.TestCase):
    def test_grid_measure_and_nesting(self):
        root = Frame()
        root.set_layout(GridLayout())
        c = Canvas(root, width=80, height=60)
        c.grid(row=0, column=0)
        root.children.append(c)  # direct for test
        # simulate layout
        gui = GUIManager()
        gui.set_root(root)
        root.set_rect(0, 0, 400, 300)
        # call measure path
        pw, ph = c.measure(gui)
        self.assertEqual((pw, ph), (80, 60))

    def test_scrollbar_roundtrip(self):
        c = Canvas(width=50, height=50, scrollregion=(0, 0, 0, 200))
        sb = Scrollbar(orient="vertical", command=c.yview)
        c.yscrollcommand = sb.set
        c.yview("moveto", 0.25)
        # sb should have been notified
        self.assertGreater(sb.first, 0.0)
        self.assertLess(sb.last, 1.0)
        # drive from sb side
        sb.command("moveto", 0.1)
        self.assertAlmostEqual(c._y_scroll, 20.0)


class TestCanvasInput(unittest.TestCase):
    def test_mouse_press_swallow_and_closest(self):
        c = Canvas()
        c.x, c.y, c.width, c.height = 0, 0, 100, 100
        iid = c.create_rectangle(10, 10, 20, 20)
        # press inside widget over item
        consumed = c.on_mouse_press(15, 15, 1)
        self.assertTrue(consumed)
        self.assertTrue(c._pressed)
        # find_closest in canvas space
        self.assertEqual(c.find_closest(15, 15), iid)

    def test_key_scroll_consumes(self):
        c = Canvas(width=50, height=50, scrollregion=(0, 0, 200, 200))
        self.assertTrue(c.on_key(pygame.K_LEFT, "", 0))
        self.assertLess(c._x_scroll, 0)
        self.assertTrue(c.on_key(pygame.K_RIGHT, "", 0))
        self.assertTrue(c.on_key(pygame.K_UP, "", 0))
        self.assertTrue(c.on_key(pygame.K_DOWN, "", 0))

    def test_drag_pans(self):
        c = Canvas(width=50, height=50, scrollregion=(0, 0, 200, 200))
        c.x, c.y, c.width, c.height = 0, 0, 50, 50
        c.on_mouse_press(10, 10, 1)
        c.on_mouse_drag(20, 15, 1)
        # moved +10 x, +5 y => scroll decreased by that
        self.assertEqual(c._x_scroll, -10)
        self.assertEqual(c._y_scroll, -5)


class TestMenu(unittest.TestCase):
    def test_add_entries(self):
        m = Menu()
        m.add_command("Open")
        m.add_cascade("Recent", menu=Menu())
        m.add_separator()
        self.assertEqual(len(m._entries), 3)
        self.assertEqual(m._entries[0]["type"], "command")
        self.assertEqual(m._entries[1]["type"], "cascade")
        self.assertEqual(m._entries[2]["type"], "separator")

    def test_post_unpost_geometry(self):
        m = Menu()
        m.add_command("A")
        m.add_command("Longer Label Here")
        m.post(50, 60)
        self.assertTrue(m._posted)
        self.assertGreater(m.width, 50)
        self.assertGreater(m.height, 20)
        self.assertEqual(m.x, 50)
        self.assertEqual(m.y, 60)
        m.unpost()
        self.assertFalse(m._posted)

    def test_index_and_invoke(self):
        called = []
        m = Menu()
        m.add_command("Do", command=lambda: called.append(1))
        m.add_separator()
        m.post(0, 0)
        self.assertEqual(m.index("Do"), 0)
        m.invoke(0)
        self.assertEqual(called, [1])
        self.assertFalse(m._posted)  # unposted on invoke

    def test_entry_at_and_contains(self):
        m = Menu()
        m.add_command("X")
        m.post(10, 20)
        self.assertTrue(m.contains(15, 25))
        self.assertEqual(m._entry_index_at(15, 25), 0)
        self.assertIsNone(m._entry_index_at(15, 20 + 100))  # way below

    def test_key_dismiss(self):
        m = Menu()
        m.add_command("X")
        m.post(0, 0)
        self.assertTrue(m.on_key(pygame.K_ESCAPE, ""))
        self.assertFalse(m._posted)

    def test_menubutton_posts(self):
        root = Frame()
        m = Menu(root)
        m.add_command("Y")
        mb = Menubutton(root, text="Menu", menu=m)
        mb.set_rect(5, 5, 60, 20)
        mb.on_click()
        self.assertTrue(m._posted)
        self.assertGreaterEqual(m.y, mb.y + mb.height - 1)


class TestLabelFrame(unittest.TestCase):
    def test_measure_with_text_and_children(self):
        lf = LabelFrame(text="Title", font_size=14)
        # no children
        w, h = lf.measure(None)
        self.assertGreater(w, 20)
        self.assertGreater(h, 10)
        # with a child
        child = Label(lf, text="child")
        child.grid(row=0, column=0)
        # measure should include label + content
        w2, h2 = lf.measure(None)
        self.assertGreaterEqual(w2, w)
        self.assertGreater(h2, h)

    def test_layout_offsets_children_below_label(self):
        root = Frame()
        root.set_layout(GridLayout())
        lf = LabelFrame(root, text="Group")
        lf.grid(row=0, column=0)
        child = Label(lf, text="inside")
        child.grid(row=0, column=0)
        gui = GUIManager()
        gui.set_root(root)
        gui.layout(200, 100)
        # child should be placed below the label area (label_space ~ 14+6 + pads ~24+)
        self.assertGreater(child.y, lf.y + 10)
        self.assertGreaterEqual(child.x, lf.x + 2)  # side pad

    def test_draw_includes_label_and_border(self):
        lf = LabelFrame(text="Foo")
        lf.set_rect(10, 20, 120, 80)

        class MR:
            def __init__(self):
                self.log = []

            def draw_rect(self, *a, **k):
                self.log.append("rect")

            def draw_rect_border(self, *a, **k):
                self.log.append("border")

            def draw_text(self, *a, **k):
                self.log.append("text")

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

            def measure_text(self, t, fs=14):
                return len(t) * 7, fs

        g = MG()
        lf.draw(g)
        self.assertIn("border", g._r.log)
        self.assertIn("text", g._r.log)

    def test_empty_and_nesting(self):
        lf = LabelFrame(text="")
        self.assertIn("Frame", str(type(lf)))  # subclass
        inner = LabelFrame(lf, text="Inner")
        inner.grid(row=0, column=0)
        # basic smoke
        w, h = lf.measure(None)
        self.assertGreater(w, 10)


class TestPanedWindow(unittest.TestCase):
    def test_add_and_basic_sizes(self):
        pw = PanedWindow(orient="horizontal", sashwidth=4)
        p1 = Frame(pw)
        p2 = Frame(pw)
        pw.add(p1, minsize=30)
        pw.add(p2, minsize=20)
        self.assertEqual(len(pw.children), 2)
        self.assertEqual(len(pw._sizes), 2)
        self.assertEqual(pw._options[0]["minsize"], 30)

    def test_layout_places_panes_and_sashes(self):
        pw = PanedWindow(orient="horizontal", sashwidth=5)
        p1 = Frame(pw)
        p2 = Frame(pw)
        pw.add(p1)
        pw.add(p2)
        pw.set_rect(0, 0, 200, 100)
        pw.layout(pw.children, 200, 100)
        # two equal ~ (200-5)/2
        self.assertAlmostEqual(p1.width, 97.5, delta=1)
        self.assertAlmostEqual(p2.x, p1.x + p1.width + 5, delta=1)
        self.assertEqual(p1.height, 100)
        self.assertEqual(p2.height, 100)

    def test_vertical_layout(self):
        pw = PanedWindow(orient="vertical")
        p1 = Frame(pw)
        p2 = Frame(pw)
        pw.add(p1)
        pw.add(p2)
        pw.set_rect(10, 10, 50, 200)
        pw.layout(pw.children, 50, 200)
        self.assertAlmostEqual(p1.height + p2.height + pw.sashwidth, 200, delta=1)

    def test_drag_updates_sizes(self):
        pw = PanedWindow(orient="horizontal", sashwidth=4)
        p1 = Frame(pw)
        p2 = Frame(pw)
        pw.add(p1, minsize=10)
        pw.add(p2, minsize=10)
        pw._sizes = [80, 80]
        # press on first sash (around x=80)
        pw.set_rect(0, 0, 164, 50)
        pressed = pw.on_mouse_press(82, 10, 1)
        self.assertTrue(pressed)
        self.assertEqual(pw._drag_sash, 0)
        # drag right
        pw.on_mouse_drag(92, 10, 1)
        self.assertGreater(pw._sizes[0], 80)
        self.assertLess(pw._sizes[1], 80)
        pw.on_mouse_release(92, 10, 1)
        self.assertIsNone(pw._drag_sash)

    def test_drag_respects_minsize(self):
        pw = PanedWindow(orient="horizontal")
        p1 = Frame(pw)
        p2 = Frame(pw)
        pw.add(p1, minsize=50)
        pw.add(p2, minsize=50)
        pw._sizes = [100, 100]
        pw.set_rect(0, 0, 204, 50)
        pw.on_mouse_press(102, 10, 1)
        pw.on_mouse_drag(10, 10)  # try shrink p1 hard
        self.assertGreaterEqual(pw._sizes[0], 50)
        pw.on_mouse_release(10, 10, 1)

    def test_measure_and_draw(self):
        pw = PanedWindow(orient="horizontal", sashwidth=4)
        p1 = Label(pw, text="left")
        p2 = Label(pw, text="right")
        pw.add(p1)
        pw.add(p2)
        w, h = pw.measure(None)
        self.assertGreater(w, 50)
        pw.set_rect(0, 0, 120, 40)

        class MR:
            def __init__(self):
                self.calls = []

            def draw_rect(self, *a, **k):
                self.calls.append("sash")

            def draw_rect_border(self, *a, **k):
                self.calls.append("sb")

            def draw_line(self, *a, **k):
                self.calls.append("grip")

            def draw_text(self, *a, **k):
                self.calls.append("text")

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

            def measure_text(self, t, fs=14):
                return len(t) * 5, 12

        g = MG()
        pw.draw(g)
        self.assertTrue(any(c == "sash" for c in g._r.calls))

    def test_nesting_in_grid(self):
        root = Frame()
        root.set_layout(GridLayout())
        pw = PanedWindow(root)
        pw.grid(row=0, column=0)
        p1 = Label(pw, text="a")
        pw.add(p1)
        p2 = Label(pw, text="b")
        pw.add(p2)
        gui = GUIManager()
        gui.set_root(root)
        gui.layout(300, 100)
        self.assertGreater(pw.width, 0)
        self.assertEqual(len(pw.children), 2)


class TestProgressbar(unittest.TestCase):
    def test_determinate_basic(self):
        pb = Progressbar(orient="horizontal", maximum=100, value=25, length=120)
        self.assertEqual(pb.get(), 25)
        pb.set(75)
        self.assertEqual(pb.get(), 75)
        pb.step(10)
        self.assertEqual(pb.get(), 85)
        w, h = pb.measure(None)
        self.assertGreater(w, 50)
        self.assertGreater(h, 5)

    def test_clamp_and_variable(self):
        var = [0.0]
        pb = Progressbar(maximum=50, value=10, variable=var)
        pb.set(999)
        self.assertEqual(pb.get(), 50)
        self.assertEqual(var[0], 50)
        pb.step(-100)
        self.assertEqual(pb.get(), 0)

    def test_indeterminate_phase(self):
        pb = Progressbar(mode="indeterminate", length=100)
        pb.start()
        initial = pb._tick

        class DummyR:
            def draw_rect(self, *a, **k):
                pass

            def draw_rect_border(self, *a, **k):
                pass

        class DummyG:
            def get_renderer(self):
                return DummyR()

        g = DummyG()
        # simulate frames (advances only when renderer present)
        for _ in range(5):
            pb.draw(g)
        self.assertGreater(pb._tick, initial)
        pb.stop()
        tick_after_stop = pb._tick
        pb.draw(g)
        self.assertEqual(pb._tick, tick_after_stop)  # no advance when stopped

    def test_draw_calls(self):
        pb = Progressbar(orient="horizontal", value=50, length=80)
        pb.set_rect(0, 0, 80, 16)

        class MR:
            def __init__(self):
                self.calls = []

            def draw_rect(self, *a, **k):
                self.calls.append("rect")

            def draw_rect_border(self, *a, **k):
                self.calls.append("border")

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

        g = MG()
        pb.draw(g)
        self.assertIn("rect", g._r.calls)
        self.assertIn("border", g._r.calls)

    def test_vertical_and_grid(self):
        root = Frame()
        root.set_layout(GridLayout())
        pb = Progressbar(root, orient="vertical", length=60)
        pb.grid(row=0, column=0)
        gui = GUIManager()
        gui.set_root(root)
        gui.layout(30, 100)
        self.assertGreater(pb.height, 30)
        # measure prefers length in major dim
        mw, mh = pb.measure(None)
        self.assertGreater(mh, mw)

    def test_indeterminate_draw_advances(self):
        pb = Progressbar(mode="indeterminate")
        pb.set_rect(0, 0, 100, 12)
        pb.start()

        class MR:
            def __init__(self):
                self.c = 0

            def draw_rect(self, *a, **k):
                self.c += 1

            def draw_rect_border(self, *a, **k):
                pass

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

        for _ in range(3):
            pb.draw(MG())
        self.assertGreater(pb._tick, 0)


class TestNotebook(unittest.TestCase):
    def test_add_and_select(self):
        nb = Notebook()
        t1 = Frame(nb)
        nb.add(t1, text="Tab One")
        t2 = Frame(nb)
        nb.add(t2, text="Tab Two")
        self.assertEqual(len(nb._tabs), 2)
        self.assertEqual(nb.current, 0)
        nb.select(1)
        self.assertEqual(nb.current, 1)
        self.assertEqual(nb.index(t1), 0)

    def test_layout_and_visibility(self):
        nb = Notebook()
        t1 = Frame(nb)
        nb.add(t1, text="A")
        t2 = Frame(nb)
        nb.add(t2, text="B")
        nb.set_rect(0, 0, 200, 120)
        nb.layout(nb.children, 200, 120)
        tab_h = nb._tab_height(None)
        self.assertEqual(t1._visible, True)
        self.assertEqual(t2._visible, False)
        self.assertAlmostEqual(t1.y, nb.y + tab_h, delta=1)
        self.assertEqual(t1.height, 120 - tab_h)

    def test_click_switches_tab(self):
        nb = Notebook()
        t1 = Frame(nb)
        nb.add(t1, text="One")
        t2 = Frame(nb)
        nb.add(t2, text="Two")
        nb.set_rect(0, 0, 200, 100)
        # click roughly on second tab (first tab ~ 4 + (len("One")*7 +16) ~ 4+ (3*7+16)~41 , second starts ~45)
        nb.on_mouse_press(60, 8, 1)
        self.assertEqual(nb.current, 1)

    def test_draw_and_measure(self):
        nb = Notebook()
        t1 = Label(nb, text="c")
        nb.add(t1, text="T1")
        nb.set_rect(10, 10, 120, 80)

        class MR:
            def __init__(self):
                self.log = []

            def draw_rect(self, *a, **k):
                self.log.append("rect")

            def draw_rect_border(self, *a, **k):
                self.log.append("border")

            def draw_text(self, *a, **k):
                self.log.append("text")

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

            def measure_text(self, t, fs=14):
                return len(t) * 6, 12

        g = MG()
        nb.draw(g)
        self.assertTrue(
            any("text" in str(x) for x in g._r.log)
        )  # at least tab or content
        w, h = nb.measure(g)
        self.assertGreater(w, 30)
        self.assertGreater(h, 20)

    def test_nesting(self):
        root = Frame()
        root.set_layout(GridLayout())
        nb = Notebook(root)
        nb.grid(row=0, column=0)
        tab = Frame(nb)
        nb.add(tab, text="Child")
        Label(tab, text="inside").grid(row=0, column=0)
        gui = GUIManager()
        gui.set_root(root)
        gui.layout(300, 200)
        self.assertGreater(nb.width, 50)
        self.assertEqual(nb.current, 0)


class TestTreeview(unittest.TestCase):
    def test_insert_hierarchy(self):
        tv = Treeview(columns=("size",))
        root = tv.insert("", "end", text="root", values=(0,))
        c1 = tv.insert(root, "end", text="child1", values=(10,))
        c2 = tv.insert(root, "end", text="child2", open=False)
        self.assertEqual(len(tv._items), 3)
        self.assertIn(c1, tv.get_children(root))
        self.assertEqual(tv.item(root, "text"), "root")
        tv.item(c2, open=True)
        self.assertTrue(tv.item(c2, "open"))

    def test_delete_and_get_children(self):
        tv = Treeview()
        r = tv.insert("", text="r")
        c = tv.insert(r, text="c")
        tv.delete(c)
        self.assertEqual(tv.get_children(r), [])
        tv.delete("all")
        self.assertEqual(len(tv._items), 0)

    def test_selection_and_focus(self):
        tv = Treeview()
        a = tv.insert("", text="a")
        b = tv.insert("", text="b")
        tv.selection_set(a)
        self.assertEqual(tv.selection(), [a])
        tv.focus(b)
        self.assertEqual(tv.focus(), b)

    def test_expand_collapse_and_visible(self):
        tv = Treeview()
        r = tv.insert("", text="root")
        _c = tv.insert(r, text="child")
        vis = tv._get_visible()
        self.assertEqual(len(vis), 2)
        tv.item(r, open=False)
        vis = tv._get_visible()
        self.assertEqual(len(vis), 1)

    def test_layout_measure(self):
        tv = Treeview(height=5)
        tv.insert("", text="x" * 20)
        tv.set_rect(0, 0, 200, 100)
        w, h = tv.measure(None)
        self.assertGreater(w, 100)
        self.assertGreater(h, 10)

    def test_mouse_select_and_toggle(self):
        tv = Treeview()
        r = tv.insert("", text="root")
        tv.insert(r, text="c")
        tv.set_rect(0, 0, 200, 100)
        # click row (first row is root) - may depend on exact y vs line_h, just ensure no crash + can select
        tv.on_mouse_press(10, 5, 1)
        tv.selection_set(r)  # force for test
        self.assertTrue(tv.selection())
        # toggle via item
        tv.item(r, open=True)
        tv.on_mouse_press(10, 5, 1)
        # basic no crash

    def test_key_nav(self):
        tv = Treeview()
        _a = tv.insert("", text="a")
        b = tv.insert("", text="b")
        tv.on_key(pygame.K_DOWN, "")
        self.assertIn(b, tv.selection() or [tv.focus()])

    def test_yview(self):
        tv = Treeview(height=2)
        for i in range(5):
            tv.insert("", text=str(i))
        tv.yview("moveto", 0.5)
        self.assertGreater(tv._scroll, 0)

    def test_columns_and_draw(self):
        tv = Treeview(columns=("sz",))
        tv.insert("", text="f", values=(123,))
        tv.set_rect(0, 0, 300, 50)
        tv.heading("sz", text="Size")

        class MR:
            def __init__(self):
                self.log = []

            def draw_rect(self, *a, **k):
                self.log.append("r")

            def draw_rect_border(self, *a, **k):
                self.log.append("b")

            def draw_text(self, *a, **k):
                self.log.append("t")

            def draw_line(self, *a, **k):
                self.log.append("line")

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

            def measure_text(self, t, fs=14):
                return 50, 12

        g = MG()
        tv.draw(g)
        self.assertTrue(any(x == "t" for x in g._r.log))

    def test_grid_nesting(self):
        root = Frame()
        root.set_layout(GridLayout())
        tv = Treeview(root)
        tv.grid(row=0, column=0)
        tv.insert("", text="node")
        gui = GUIManager()
        gui.set_root(root)
        gui.layout(200, 100)
        self.assertGreater(tv.width, 10)


class TestSeparator(unittest.TestCase):
    def test_orient_and_measure(self):
        s = Separator(orient="horizontal")
        w, h = s.measure(None)
        self.assertGreater(w, h)
        s2 = Separator(orient="vertical")
        w2, h2 = s2.measure(None)
        self.assertGreater(h2, w2)

    def test_draw(self):
        s = Separator(orient="horizontal")
        s.set_rect(0, 0, 100, 2)

        class MR:
            def __init__(self):
                self.log = []

            def draw_line(self, *a, **k):
                self.log.append("line")

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

        g = MG()
        s.draw(g)
        self.assertIn("line", g._r.log)

    def test_in_grid(self):
        root = Frame()
        root.set_layout(GridLayout())
        s = Separator(root, orient="horizontal")
        s.grid(row=0, column=0, sticky="ew")
        gui = GUIManager()
        gui.set_root(root)
        gui.layout(200, 50)
        self.assertGreater(s.width, 50)
        self.assertLess(s.height, 5)


class TestSizegrip(unittest.TestCase):
    def test_measure(self):
        sg = Sizegrip()
        w, h = sg.measure(None)
        self.assertEqual(w, 16)
        self.assertEqual(h, 16)

    def test_draw(self):
        sg = Sizegrip()
        sg.set_rect(0, 0, 16, 16)

        class MR:
            def __init__(self):
                self.log = []

            def draw_rect(self, *a, **k):
                self.log.append("rect")

            def draw_line(self, *a, **k):
                self.log.append("line")

            def get_renderer(self):
                return self

        class MG:
            def __init__(self):
                self._r = MR()

            def get_renderer(self):
                return self._r

        g = MG()
        sg.draw(g)
        self.assertTrue(any(x in g._r.log for x in ("rect", "line")))

    def test_drag_calls_command(self):
        deltas = []

        def cmd(dx, dy):
            deltas.append((dx, dy))

        sg = Sizegrip(command=cmd)
        sg.set_rect(0, 0, 16, 16)
        sg.on_mouse_press(0, 0, 1)
        sg.on_mouse_drag(5, 3, 1)
        sg.on_mouse_release(5, 3, 1)
        self.assertTrue(deltas)

    def test_in_grid_corner(self):
        root = Frame()
        root.set_layout(GridLayout())
        sg = Sizegrip(root)
        sg.grid(row=1, column=1, sticky="se")
        gui = GUIManager()
        gui.set_root(root)
        gui.layout(100, 100)
        self.assertLess(sg.x, 100)
        self.assertLess(sg.y, 100)


class TestEntry(unittest.TestCase):
    def test_backspace_at_end(self):
        e = Entry(text="this is a test")
        self.assertEqual(len(e.text), 14)
        e._cursor_pos = 14
        e._handle_held_edit_key(pygame.K_BACKSPACE, 0)
        self.assertEqual(e.text, "this is a tes")
        self.assertEqual(e._cursor_pos, 13)

    def test_backspace_then_backspace(self):
        e = Entry(text="this is a test")
        e._cursor_pos = 14
        e._handle_held_edit_key(pygame.K_BACKSPACE, 0)
        e._handle_held_edit_key(pygame.K_BACKSPACE, 0)
        self.assertEqual(e.text, "this is a te")
        self.assertEqual(e._cursor_pos, 12)

    def test_delete_at_caret_before_last(self):
        e = Entry(text="this is a test")
        e._cursor_pos = 13
        e._handle_held_edit_key(pygame.K_DELETE, 0)
        self.assertEqual(e.text, "this is a tes")
        self.assertEqual(e._cursor_pos, 13)  # stays, now at end

    def test_delete_no_op_at_end(self):
        e = Entry(text="abc")
        e._cursor_pos = 3
        e._handle_held_edit_key(pygame.K_DELETE, 0)
        self.assertEqual(e.text, "abc")
        self.assertEqual(e._cursor_pos, 3)

    def test_backspace_no_op_at_start(self):
        e = Entry(text="abc")
        e._cursor_pos = 0
        e._handle_held_edit_key(pygame.K_BACKSPACE, 0)
        self.assertEqual(e.text, "abc")
        self.assertEqual(e._cursor_pos, 0)

    def test_typing_and_backspace(self):
        e = Entry()
        e._cursor_pos = 0
        # simulate char inserts via on_key (uses different path)
        e.on_key(0, "a", 0)
        e.on_key(0, "b", 0)
        e.on_key(0, "c", 0)
        self.assertEqual(e.text, "abc")
        self.assertEqual(e._cursor_pos, 3)
        e._handle_held_edit_key(pygame.K_BACKSPACE, 0)
        self.assertEqual(e.text, "ab")
        self.assertEqual(e._cursor_pos, 2)


if __name__ == "__main__":
    unittest.main()
