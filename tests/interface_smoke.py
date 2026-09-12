"""Check native window restoration and the information overlay without moving the mouse."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from spotlight import Spotlight

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
c = Spotlight(app, persist=False)
user32 = ctypes.WinDLL("user32")
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32 = ctypes.WinDLL("kernel32")
try:
    c.show_panel()
    c.select()
    QTest.qWait(150)
    assert c.panel.isMinimized()
    assert user32.PostThreadMessageW(kernel32.GetCurrentThreadId(), 0x0312, 3, 0)
    QTest.qWait(150)
    assert c.mode == "off"
    assert c.panel.isVisible() and not c.panel.isMinimized()
    assert not user32.GetWindowLongW(int(c.panel.winId()), -20) & 0x80
    assert c.panel.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert user32.GetForegroundWindow() == int(c.panel.winId())
    c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "panel-preview.png"))
    c.panel.info_button.click()
    QTest.qWait(150)
    assert c.panel.information.isVisible()
    c.panel.information.grab().save(str(Path(__file__).resolve().parents[1] / "information-preview.png"))
    QTest.keyClick(c.panel.information, Qt.Key.Key_Escape)
    assert not c.panel.information.isVisible()
    assert c.panel.isVisible()
    print("PASS: Escape restores foreground taskbar window; information opens and dismisses")
finally:
    c.shutdown()
    c.panel.hide()
