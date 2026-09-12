"""Brief visible Windows smoke check. Run manually: py tests/native_smoke.py."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPoint, QRectF
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtTest import QTest

from spotlight import Spotlight


def main():
    if sys.platform != "win32":
        raise SystemExit("This check requires Windows.")
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    c = Spotlight(app, persist=False)
    target = QWidget()
    target.setWindowTitle("Screen Spotlight verification target")
    area = app.primaryScreen().availableGeometry()
    target.setGeometry(area.x() + 100, area.y() + 100, 440, 320)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostThreadMessageW.restype = wintypes.BOOL
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    saved_cursor = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(saved_cursor))
    dragging = False

    def process():
        for _ in range(12):
            app.processEvents()

    try:
        target.show()
        target.raise_()
        target.activateWindow()
        process()
        c.selected_screen = app.primaryScreen()
        start = target.mapToGlobal(QPoint(120, 100))
        c.focus = QRectF(start.x(), start.y(), 160, 120)
        c.panel.dim_buttons[100].click()
        c.lock()
        process()
        overlay = next(o for o in c.overlays if o.screen_ref == app.primaryScreen())
        style = user32.GetWindowLongW(int(overlay.winId()), -20)
        assert style & 0x20, "Native WS_EX_TRANSPARENT is missing"
        assert style & 0x80000, "Native WS_EX_LAYERED is missing"
        # ClientToScreen uses physical coordinates, including on scaled monitors.
        scale = target.devicePixelRatioF()
        for x, y in [(30, 150), (180, 150)]:
            point = wintypes.POINT(round(x * scale), round(y * scale))
            assert user32.ClientToScreen(int(target.winId()), ctypes.byref(point))
            hit = user32.WindowFromPoint(point)
            assert hit == int(target.winId()), f"Overlay intercepted native hit test at {x}, {y}: {hit}"
        print("PASS: Native click-through hit tests inside and outside spotlight")
        c.edit()
        process()
        style = user32.GetWindowLongW(int(overlay.winId()), -20)
        assert not style & 0x20, "Editing still has WS_EX_TRANSPARENT"
        print("PASS: Editing restores native mouse input")
        original = QRectF(c.focus)
        local = overlay.local_rect().center()
        scale = overlay.devicePixelRatioF()
        point = wintypes.POINT(round(local.x() * scale), round(local.y() * scale))
        assert user32.ClientToScreen(int(overlay.winId()), ctypes.byref(point))
        assert user32.WindowFromPoint(point) == int(overlay.winId()), "Edit hole does not receive native mouse input"
        user32.SetCursorPos(point.x, point.y)
        QTest.qWait(80)
        dragging = True
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        QTest.qWait(80)
        user32.SetCursorPos(point.x + round(40 * scale), point.y + round(30 * scale))
        QTest.qWait(80)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        dragging = False
        QTest.qWait(80)
        assert abs(c.focus.x() - original.x() - 40) <= 1, (original, c.focus)
        assert abs(c.focus.y() - original.y() - 30) <= 1, (original, c.focus)
        assert c.focus.size() == original.size()
        print("PASS: Real Windows mouse drag moves the existing area without resizing it")
        assert not c.hotkey_errors, c.hotkey_errors
        assert 3 in c.hotkeys.registered, "Escape hotkey registration failed"
        assert user32.PostThreadMessageW(kernel32.GetCurrentThreadId(), 0x0312, 3, 0)
        process()
        assert c.mode == "off", "Native WM_HOTKEY was not dispatched"
        assert 3 not in c.hotkeys.registered, "Escape was not released"
        print("PASS: Global shortcut registration, native dispatch, and Escape cleanup")
        for ident, expected in [(1, "select"), (4, "off")]:
            assert user32.PostThreadMessageW(kernel32.GetCurrentThreadId(), 0x0312, ident, 0)
            process()
            assert c.mode == expected, f"Hotkey {ident} did not enter {expected}"
            assert c.panel.isVisible()
            assert c.panel.isMinimized() == (expected == "select"), "Unexpected control panel state"
        print("PASS: New-area minimizes controls and clear restores them")
        c.show_panel()
        c.select()
        process()
        assert c.panel.isVisible() and c.panel.isMinimized(), "Controls were hidden instead of minimized"
        panel_style = user32.GetWindowLongW(int(c.panel.winId()), -20)
        assert not panel_style & 0x80, "Control panel is a tool window excluded from Alt+Tab"
        assert user32.PostThreadMessageW(kernel32.GetCurrentThreadId(), 0x0312, 5, 0)
        process()
        assert c.panel.isVisible() and not c.panel.isMinimized(), "Controls shortcut did not restore panel"
        c.clear()
        print("PASS: Controls remain a normal minimized window and Ctrl+Shift+P restores them")
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "panel-preview.png"))
    finally:
        if dragging:
            user32.mouse_event(0x0004, 0, 0, 0, 0)
        user32.SetCursorPos(saved_cursor.x, saved_cursor.y)
        c.shutdown()
        target.close()
        c.panel.hide()
    print("Windows smoke check passed.")


if __name__ == "__main__":
    main()
