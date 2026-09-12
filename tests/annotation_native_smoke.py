"""Windows input and capture verification; briefly shows a white test window."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QToolTip, QWidget
from spotlight import Spotlight


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    c = Spotlight(app, native_hotkeys=False, persist=False)
    a = c.annotations
    saved_cursor = QCursor.pos()
    target = QWidget()
    target.setStyleSheet("background: white;")
    target.setGeometry(app.primaryScreen().availableGeometry().adjusted(40, 40, -40, -40))
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]

    def hit(widget, point):
        ratio = widget.devicePixelRatioF()
        native = wintypes.POINT(round(point.x() * ratio), round(point.y() * ratio))
        assert user32.ClientToScreen(int(widget.winId()), ctypes.byref(native))
        return user32.WindowFromPoint(native)

    try:
        target.show()
        target.raise_()
        QTest.qWait(150)
        origin = target.mapToGlobal(QPoint(100, 100))
        c.selected_screen = app.primaryScreen()
        c.focus = QRectF(origin.x(), origin.y(), 300, 200)
        c.panel.tabs.setCurrentIndex(1)
        assert a.drawing and a.tool == "pen", "Opening Annotation must activate pen immediately"
        c.panel.move(origin.x() + 350, target.y())
        QTest.qWait(150)
        assert c.panel.isVisible() and not c.panel.isMinimized(), "Controls disappeared when choosing a tool"
        button = a.tool_buttons["pen"]
        panel_point = button.mapTo(c.panel, button.rect().center())
        assert hit(c.panel, panel_point) == int(c.panel.winId()), "Controls are covered by the ink surface"
        local = a.overlay.mapFromGlobal(origin)
        assert hit(a.overlay, local + QPoint(30, 30)) == int(a.overlay.winId()), "Blank ink surface must receive drawing input"
        a.width.setValue(12)
        QTest.mousePress(a.overlay, Qt.MouseButton.LeftButton, pos=local + QPoint(20, 40))
        QTest.mouseRelease(a.overlay, Qt.MouseButton.LeftButton, pos=local + QPoint(100, 40))
        assert c.panel.isVisible() and not c.panel.isMinimized(), "Drawing hid the controls"
        a.overlay.raise_()
        QTest.qWait(100)
        assert hit(c.panel, panel_point) == int(c.panel.winId()), "Raised drawing surface blocks controls"
        QTest.mouseClick(a.tool_buttons["arrow"], Qt.MouseButton.LeftButton)
        assert a.drawing and a.tool == "arrow", "Tool switch needs another start action"
        assert len(a.marks) == 1, "Clicking a tool drew behind controls"
        c.panel.move(c.panel.pos() + QPoint(10, 10))
        QTest.qWait(100)
        panel_point = a.tool_buttons["arrow"].mapTo(c.panel, a.tool_buttons["arrow"].rect().center())
        assert hit(c.panel, panel_point) == int(c.panel.winId()), "Moved controls are covered by ink"
        a.interact()
        QTest.qWait(100)
        assert hit(target, QPoint(150, 140)) == int(target.winId()), "Ink must allow clicks through after Interact"
        c.show_panel()
        c.panel.move(origin)
        QTest.qWait(100)
        a.capture()
        QTest.qWait(650)
        assert not a.captured.isNull(), a.status.text()
        image = a.captured.toImage()
        ratio = a.captured.devicePixelRatio()
        red = image.pixelColor(round(50 * ratio), round(40 * ratio))
        white = image.pixelColor(round(150 * ratio), round(100 * ratio))
        assert red.red() > 180 and red.green() < 100, f"Capture missed ink: {red.name()}"
        assert min(white.red(), white.green(), white.blue()) > 245, f"Controls leaked into capture: {white.name()}"
        assert image.width() == round(300 * ratio) and image.height() == round(200 * ratio)
        c.panel.tabs.setCurrentIndex(1)
        c.panel.adjustSize()
        QTest.qWait(100)
        assert c.panel.height() <= app.primaryScreen().availableGeometry().height(), "Controls exceed screen height"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-panel-preview.png"))
        a.tool_buttons["letter"].click()
        a.sequence.setValue(8)
        a.copy_button.setEnabled(False)
        a.save_button.setEnabled(False)
        QTest.qWait(100)
        assert a.sequence.text() == "H", "Letter field shows a number"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-letter-preview.png"))
        c.panel.tabs.setCurrentIndex(0)
        QTest.qWait(100)
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "spotlight-panel-preview.png"))
        c.panel.tabs.setCurrentIndex(1)
        a.overlay.activateWindow()
        QTest.qWait(100)
        pen = a.tool_buttons["pen"]
        QTest.mouseMove(pen, pen.rect().center())
        QTest.qWait(2000)
        assert QToolTip.isVisible() and QToolTip.text().startswith("Pen:"), (
            f"Icon tooltip missing: text={QToolTip.text()!r}, hover={pen.underMouse()}, "
            f"pointer={QCursor.pos()}, target={pen.mapToGlobal(pen.rect().center())}")
        QToolTip.hideText()
        print("PASS: Native drawing input, click-through, annotated area capture, controls exclusion, and panel layout")
    finally:
        QCursor.setPos(saved_cursor)
        c.shutdown()
        c.panel.hide()
        target.hide()


if __name__ == "__main__":
    main()
