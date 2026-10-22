"""Windows regressions for compact controls and desktop/drawing transitions."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from spotlight import Spotlight


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    c = Spotlight(app, native_hotkeys=False, persist=False)
    a = c.annotations
    cursor = QCursor.pos()
    target = QWidget()
    target.setGeometry(app.primaryScreen().availableGeometry().adjusted(20, 20, -20, -20))
    target.setStyleSheet("background: white")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]

    def hit(widget, point):
        ratio = widget.devicePixelRatioF()
        point = wintypes.POINT(round(point.x() * ratio), round(point.y() * ratio))
        assert user32.ClientToScreen(int(widget.winId()), ctypes.byref(point))
        return user32.WindowFromPoint(point)

    try:
        target.show()
        target.raise_()
        c.show_panel()
        c.panel.move(650, 100)
        c.panel.tabs.setCurrentIndex(1)
        QTest.qWait(120)
        assert c.panel.size() == QSize(400, 400)
        for size in (QSize(360, 320), QSize(400, 400), QSize(700, 900)):
            c.panel.resize(size)
            for index in (0, 1):
                c.panel.tabs.setCurrentIndex(index)
                QTest.qWait(50)
                assert c.panel.size() == size
                scroll = c.panel.tabs.widget(index)
                assert scroll.horizontalScrollBar().maximum() == 0, "Content clipped at compact width"
                assert c.panel.rect().contains(c.panel.version_label.geometry())
                scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                QTest.qWait(40)
        c.panel.resize(400, 400)
        c.panel.tabs.setCurrentIndex(1)
        c.panel.annotation_scroll.verticalScrollBar().setValue(0)
        point = a.overlay.mapFromGlobal(target.mapToGlobal(QPoint(100, 100)))
        for tool in a.tool_specs:
            a.set_tool(tool)
            QTest.qWait(40)
            assert a.tools.checkedButton() == a.tool_buttons[tool]
            if tool != "laser":
                assert hit(a.overlay, point) == int(a.overlay.winId()), tool
            a.interact_button.click()
            QTest.qWait(40)
            assert not a.drawing and a.tools.checkedButton() == a.interact_button
            assert hit(target, QPoint(100, 100)) == int(target.winId()), tool
            a.interact_button.click()
            QTest.qWait(40)
            assert a.drawing and a.tool == tool
            if tool != "laser":
                assert hit(a.overlay, point) == int(a.overlay.winId()), tool
        for tool, field, text, value in (
                ("pen", a.pen_width, "12", 12), ("highlighter", a.highlighter_width, "32", 32),
                ("rectangle", a.shape_width, "7", 7), ("number", a.size, "60", 60),
                ("laser", a.laser_size, "24", 24), ("number", a.sequence, "123456", 123456),
                ("letter", a.sequence, "AZ", 52)):
            a.set_tool(tool)
            c.panel.annotation_scroll.ensureWidgetVisible(field)
            c.panel.activateWindow()
            QTest.qWait(50)
            assert field.rect().contains(field.up_arrow.geometry())
            assert field.rect().contains(field.down_arrow.geometry()), "Arrow controls clipped by field height"
            QTest.mouseClick(field.lineEdit(), Qt.MouseButton.LeftButton)
            QTest.keyClick(field.lineEdit(), Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
            QTest.keyClicks(field.lineEdit(), text)
            QTest.keyClick(field.lineEdit(), Qt.Key.Key_Return)
            assert field.value() == value, (tool, field.value())
            assert a.drawing
        c.panel.annotation_scroll.ensureWidgetVisible(a.sequence)
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "compact-settings-preview.png"))
        print("PASS: native click-through and drawing resume for all tools; compact resize/scroll; typed sizes and markers")
    finally:
        c.shutdown()
        c.panel.hide()
        target.hide()
        QCursor.setPos(cursor)


if __name__ == "__main__":
    main()
