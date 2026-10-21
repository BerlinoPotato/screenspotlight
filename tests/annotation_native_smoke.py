"""Windows input and capture verification; briefly shows a white test window."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QAbstractNativeEventFilter, QEvent, QObject, QMimeData, QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtGui import QColor, QCursor, QImage
from PySide6.QtWidgets import QApplication, QMessageBox, QToolTip, QWidget
from spotlight import Spotlight


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    c = Spotlight(app, native_hotkeys=False, persist=False)
    a = c.annotations
    saved_cursor = QCursor.pos()
    saved_clipboard = QMimeData()
    for format_name in app.clipboard().mimeData().formats():
        saved_clipboard.setData(format_name, app.clipboard().mimeData().data(format_name))
    target = QWidget()
    target.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
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
        c.edit()
        spotlight_overlay = next(o for o in c.overlays if o.screen_ref == c.selected_screen)
        original_area = QRectF(c.focus)
        drag_point = spotlight_overlay.mapFromGlobal(origin) + QPoint(140, 100)
        QTest.mousePress(spotlight_overlay, Qt.MouseButton.LeftButton, pos=drag_point)
        c.geometry_changed()
        QTest.mouseRelease(spotlight_overlay, Qt.MouseButton.LeftButton, pos=drag_point + QPoint(20, 10))
        assert c.focus == original_area.translated(20, 10), "Layout notification interrupted spotlight movement"
        c.focus = original_area
        resize_point = spotlight_overlay.mapFromGlobal(origin) + QPoint(300, 100)
        QTest.mousePress(spotlight_overlay, Qt.MouseButton.LeftButton, pos=resize_point)
        c.screens_changed()
        QTest.mouseRelease(spotlight_overlay, Qt.MouseButton.LeftButton, pos=resize_point + QPoint(30, 0))
        assert c.focus.width() == 330, "Layout notification interrupted spotlight resizing"
        c.focus = original_area
        c.repaint()
        class SurfaceEvents(QObject):
            def __init__(self):
                super().__init__()
                self.hidden = []
                self.panel_resizes = []

            def eventFilter(self, widget, event):
                if event.type() == QEvent.Type.Hide:
                    self.hidden.append(widget.windowTitle())
                if widget is c.panel and event.type() == QEvent.Type.Resize:
                    self.panel_resizes.append(widget.size())
                return False

        class NativeSurfaceEvents(QAbstractNativeEventFilter):
            def __init__(self):
                super().__init__()
                self.windows = set()
                self.layer_drops = []
                self.proposed_drops = 0

            def nativeEventFilter(self, event_type, message):
                msg = wintypes.MSG.from_address(int(message))
                if msg.hWnd in self.windows and msg.message in (0x007C, 0x007D) and ctypes.c_ssize_t(msg.wParam).value == -20:
                    styles = (wintypes.DWORD * 2).from_address(msg.lParam)
                    if styles[0] & 0x80000 and not styles[1] & 0x80000:
                        if msg.message == 0x007C:
                            self.proposed_drops += 1
                        else:
                            self.layer_drops.append((msg.hWnd, styles[0], styles[1]))
                return False, 0

        native_watcher = NativeSurfaceEvents()
        app.installNativeEventFilter(native_watcher)
        native_watcher.windows.add(int(spotlight_overlay.winId()))
        watcher = SurfaceEvents()
        c.show_panel()
        QTest.qWait(80)
        panel_bounds = c.panel.geometry()
        for widget in (c.panel, spotlight_overlay):
            widget.installEventFilter(watcher)
        c.panel.tabs.setCurrentIndex(1)
        QTest.qWait(80)
        assert c.panel.geometry() == panel_bounds, "First tab switch resized the controls"
        assert not watcher.hidden, f"First tab switch hid a visible surface: {watcher.hidden}"
        a.overlay.installEventFilter(watcher)
        ink_id = int(a.overlay.winId())
        native_watcher.windows.add(ink_id)
        spotlight_id = int(spotlight_overlay.winId())
        for index in (0, 1, 0, 1):
            c.panel.tabs.setCurrentIndex(index)
            QTest.qWait(80)
            assert c.panel.geometry() == panel_bounds, "Switching tabs resized or moved the controls"
            assert int(a.overlay.winId()) == ink_id and int(spotlight_overlay.winId()) == spotlight_id
        for tool in ("letter", "number", "laser", "move", "filled_rectangle", "pen"):
            a.set_tool(tool)
            QTest.qWait(80)
            assert c.panel.geometry() == panel_bounds, f"{tool} changed the shared control window size"
        assert not watcher.hidden, f"Tab switches hid a visible surface: {watcher.hidden}"
        assert not watcher.panel_resizes, f"Tab switches resized the controls: {watcher.panel_resizes}"
        assert native_watcher.proposed_drops, "Native check did not exercise Qt's layered-surface reset"
        assert not native_watcher.layer_drops, f"Input transitions dropped native overlay pixels: {native_watcher.layer_drops}"
        app.removeNativeEventFilter(native_watcher)
        for widget in (c.panel, spotlight_overlay, a.overlay):
            widget.removeEventFilter(watcher)
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
        before_move = list(a.marks[0].points)
        a.tool_buttons["move"].click()
        QTest.qWait(80)
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-move-preview.png"))
        QTest.mousePress(a.overlay, Qt.MouseButton.LeftButton, pos=local + QPoint(60, 40))
        QTest.mouseRelease(a.overlay, Qt.MouseButton.LeftButton, pos=local + QPoint(100, 70))
        assert a.marks[0].points == [p + QPointF(40, 30) for p in before_move], "Move did not translate the native stroke"
        a.undo()
        assert a.marks[0].points == before_move, "Undo failed to restore the moved stroke"
        assert c.focus == original_area, "Moving annotations changed the spotlight area"
        def confirm_screen_move(answer):
            failures = []

            def respond():
                dialog = app.activeModalWidget()
                try:
                    assert isinstance(dialog, QMessageBox) and dialog.isVisible(), "Screen move lacks a visible confirmation"
                    assert dialog.defaultButton() is dialog.button(QMessageBox.StandardButton.Cancel), "Screen move must default to Cancel"
                    button = dialog.button(answer)
                    point = button.mapTo(dialog, button.rect().center())
                    assert hit(dialog, point) == int(dialog.winId()), "Confirmation is blocked by an overlay"
                    dialog.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-screen-confirm-preview.png"))
                    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                except Exception as error:
                    failures.append(error)
                    if dialog is not None:
                        dialog.reject()

            QTimer.singleShot(150, respond)
            a.move_screen_button.click()
            assert not failures, failures

        # Exercise real cross-monitor and mixed-DPI moves without repinning ink.
        pinned = a.screen
        ink_bounds = a.overlay.geometry()
        saved_panel_position = c.panel.pos()
        saved_marks = list(a.marks)
        saved_history, saved_future = list(a.history), list(a.future)
        for other in (s for s in app.screens() if s != pinned):
            c.panel.move(other.availableGeometry().topLeft() + QPoint(40, 40))
            QTest.qWait(180)
            assert c.panel.screen() == other, "Controls did not reach the test monitor"
            a.set_tool("move")
            QTest.mouseClick(a.overlay, Qt.MouseButton.LeftButton, pos=local + QPoint(60, 40))
            c.geometry_changed()
            assert a.screen == pinned and a.overlay.geometry() == ink_bounds, "Controls moved the annotation area"
            assert a.marks == saved_marks and a.history == saved_history and a.future == saved_future, "Monitor/tool/selection change deleted ink or undo history"
            assert a.move_screen_button.isEnabled(), "Explicit screen move unavailable"
            confirm_screen_move(QMessageBox.StandardButton.Cancel)
            assert a.screen == pinned and a.marks == saved_marks, "Cancel moved or cleared annotations"
            confirm_screen_move(QMessageBox.StandardButton.Yes)
            assert a.screen == other and a.overlay.geometry() == other.geometry(), "Confirmed move did not change screens"
            assert a.marks == saved_marks and a.history == saved_history and a.future == saved_future, "Confirmed move lost ink/history"
            c.panel.move(saved_panel_position)
            QTest.qWait(180)
            confirm_screen_move(QMessageBox.StandardButton.Yes)
            assert a.screen == pinned and a.overlay.geometry() == ink_bounds
        c.panel.move(saved_panel_position)
        a.interact()
        QTest.qWait(100)
        window = hit(target, QPoint(150, 140))
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW(window, title, len(title))
        assert window == int(target.winId()), (
            f"Ink must allow clicks through after Interact: hit={window}, title={title.value!r}, "
            f"target={int(target.winId())}, ink={int(a.overlay.winId())}, "
            f"spotlight={[int(o.winId()) for o in c.overlays]}, flags={a.overlay.windowFlags()}")
        c.show_panel()
        c.panel.move(origin)
        QTest.qWait(100)
        a.capture_button.click()
        QTest.qWait(650)
        assert a.status.text() == "Copied to clipboard", a.status.text()
        assert app.clipboard().pixmap().toImage() == a.captured.toImage(), "Clipboard missed fresh capture"
        assert not a.captured.isNull(), a.status.text()
        image = a.captured.toImage()
        ratio = a.captured.devicePixelRatio()
        red = image.pixelColor(round(50 * ratio), round(40 * ratio))
        white = image.pixelColor(round(150 * ratio), round(100 * ratio))
        assert red.red() > 180 and red.green() < 100, f"Capture missed ink: {red.name()}"
        assert min(white.red(), white.green(), white.blue()) > 245, f"Controls leaked into capture: {white.name()}"
        assert image.width() == round(300 * ratio) and image.height() == round(200 * ratio)
        # Save Image must capture the changed desktop, independent of Capture Image.
        with tempfile.TemporaryDirectory(prefix="spotlight-native-save-") as folder:
            saved_path = Path(folder) / "new capture.png"
            target.setStyleSheet("background: #e8f0ff;")
            QTest.qWait(100)
            previous_clipboard = app.clipboard().pixmap().toImage()
            with patch("annotations.QFileDialog.getSaveFileName", return_value=(str(saved_path), "PNG image (*.png)")) as dialog:
                a.save_button.click()
                assert a.capturing and not c.panel.isVisible(), "Save must take a new capture"
                QTest.qWait(650)
                dialog.assert_called_once()
            assert a.status.text() == "Image saved", a.status.text()
            saved_image = QImage(str(saved_path))
            assert saved_image.size() == image.size(), "Saved crop has the wrong size"
            saved_background = saved_image.pixelColor(round(150 * ratio), round(100 * ratio))
            assert saved_background == QColor("#e8f0ff"), f"Save reused a stale capture: {saved_background.name()}"
            assert app.clipboard().pixmap().toImage() == previous_clipboard, "Save changed clipboard contents"
            assert a.capture_button.isEnabled() and a.save_button.isEnabled()
            target.setStyleSheet("background: white;")
        c.panel.tabs.setCurrentIndex(1)
        c.panel.adjustSize()
        QTest.qWait(100)
        assert c.panel.height() <= app.primaryScreen().availableGeometry().height(), "Controls exceed screen height"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-panel-preview.png"))
        normal_size = c.panel.size()
        a.variant.button(1).click()
        a.swatches.button(7).click()
        QTest.qWait(220)
        assert a.swatches.button(7).color.name() == "#212121", "Pastel is missing the final black swatch"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-pastel-preview.png"))
        a.variant.button(0).click()
        a.swatches.button(0).click()
        a.tool_actions["letter"].trigger()
        QTest.qWait(80)
        assert c.panel.size() == normal_size, "Marker controls changed the shared window size"
        a.sequence.setValue(8)
        QTest.qWait(100)
        assert a.sequence.text() == "H", "Letter field shows a number"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-letter-preview.png"))
        c.panel.move(origin.x() + 350, target.y())
        a.set_tool("laser")
        a.laser_size.setValue(32)
        QCursor.setPos(origin + QPoint(150, 140))
        QTest.qWait(200)
        assert a.overlay.laser_point is not None, "Laser failed to follow the real mouse"
        assert c.system_cursor.hidden, "Windows rejected hiding the normal cursor"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-laser-preview.png"))
        assert hit(target, QPoint(250, 240)) == int(target.winId()), "Laser blocks desktop input"
        laser_image = app.primaryScreen().grabWindow(0).toImage()
        laser_global = origin + QPoint(163, 140)
        laser_pixel = laser_image.pixelColor(round(laser_global.x() * ratio), round(laser_global.y() * ratio))
        assert laser_pixel.red() > 180 and laser_pixel.green() < 130, f"Laser is not visible: {laser_pixel.name()}"
        QCursor.setPos(c.panel.mapToGlobal(QPoint(30, 30)))
        QTest.qWait(100)
        assert not c.system_cursor.hidden, "Normal cursor did not return over controls"
        QCursor.setPos(origin + QPoint(150, 140))
        QTest.qWait(100)
        assert c.system_cursor.hidden, "Normal cursor reappeared over the laser surface"
        count = len(a.marks)
        c.escape()
        assert not c.system_cursor.hidden, "Normal cursor did not return when laser stopped"
        assert not a.overlay.laser_timer.isActive() and a.overlay.laser_point is None
        assert len(a.marks) == count, "Laser changed permanent ink"
        a.set_tool("pen")
        assert not a.overlay.windowHandle().flags() & Qt.WindowType.WindowTransparentForInput
        fixed_size = c.panel.size()
        c.panel.tabs.setCurrentIndex(0)
        QTest.qWait(100)
        assert c.panel.size() == fixed_size, "Spotlight and Annotation have different window sizes"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "spotlight-panel-preview.png"))
        c.panel.tabs.setCurrentIndex(1)
        a.overlay.activateWindow()
        QTest.qWait(100)
        pen = a.tool_buttons["pen"]
        pen_panel_point = pen.mapTo(c.panel, pen.rect().center())
        assert hit(c.panel, pen_panel_point) == int(c.panel.winId()), "Ink or another window blocks native toolbar hover"
        QCursor.setPos(origin + QPoint(150, 140))
        QTest.qWait(100)
        QTest.mouseMove(pen, pen.rect().center())
        QTest.qWait(2000)
        assert QToolTip.isVisible() and QToolTip.text().startswith("Pen:"), (
            f"Icon tooltip missing: text={QToolTip.text()!r}, hover={pen.underMouse()}, "
            f"pointer={QCursor.pos()}, target={pen.mapToGlobal(pen.rect().center())}")
        QToolTip.hideText()
        group = a.tool_buttons["rectangle"]
        QTest.mouseClick(group, Qt.MouseButton.RightButton)
        QTest.qWait(100)
        assert group.tool_menu.isVisible(), "Right-click did not open the shape menu"
        group.tool_menu.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-tools-menu-preview.png"))
        action = a.tool_actions["filled_rectangle"]
        QTest.mouseClick(group.tool_menu, Qt.MouseButton.LeftButton,
                         pos=group.tool_menu.actionGeometry(action).center())
        assert a.tool == "filled_rectangle", "Native menu selection did not choose the filled tool"
        c.panel.grab().save(str(Path(__file__).resolve().parents[1] / "annotation-grouped-preview.png"))
        print("PASS: Native drawing, grouped icon menus, laser-only cursor/restoration, moving marks, spotlight stability, constant tab geometry without native surface resets, pinned ink across real mixed-DPI monitors, confirmed screen moves, both black palettes, two image actions with fresh clipboard/file pixels, controls exclusion, and layout")
    finally:
        QCursor.setPos(saved_cursor)
        app.clipboard().setMimeData(saved_clipboard)
        c.shutdown()
        c.panel.hide()
        target.hide()


if __name__ == "__main__":
    main()
