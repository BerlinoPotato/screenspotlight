"""Regressions for deliberate monitor selection and shared controls."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QWheelEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtTest import QTest
from annotations import Mark
from spotlight import Hotkeys, Spotlight

class ImprovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.c = Spotlight(self.app, native_hotkeys=False, persist=False)
        self.a = self.c.annotations

    def tearDown(self):
        self.c.shutdown()
        self.c.panel.hide()
        self.a.overlay.deleteLater()
        for overlay in self.c.overlays:
            overlay.deleteLater()
        self.c.panel.deleteLater()
        self.app.processEvents()

    def other_screen(self):
        screen = Mock()
        screen.name.return_value = "Left monitor"
        screen.serialNumber.return_value = "left-serial"
        screen.manufacturer.return_value = "Test"
        screen.model.return_value = "Display"
        screen.geometry.return_value = QRect(-1200, -100, 1200, 900)
        return screen

    def test_monitor_map_escape_keeps_drawing_and_target(self):
        self.a.start()
        target = self.a.screen
        self.a.screen_selector.showPopup()
        self.assertIsNotNone(self.app.activePopupWidget())
        self.c.escape()
        self.assertFalse(self.a.screen_selector.monitor_popup.isVisible())
        self.assertTrue(self.a.drawing)
        self.assertIs(self.a.screen, target)

    def test_monitor_map_cancel_keeps_annotations(self):
        primary = self.app.primaryScreen()
        other = self.other_screen()
        self.a.start()
        mark = Mark("pen", "#e53935", 4, 40, [QPointF(100, 120)])
        self.a.marks = [mark]
        with patch.object(self.app, "screens", return_value=[primary, other]):
            self.a.sync_screen_controls()
            self.a.screen_selector.showPopup()
            with patch("annotations.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel):
                self.a.screen_selector.monitor_popup.tiles[1].click()
            self.assertIs(self.a.screen, primary)
            self.assertEqual(self.a.marks, [mark])
            self.assertTrue(self.a.drawing)

    def test_monitor_map_qt_escape_then_poll_consumes_same_press(self):
        self.a.start()
        self.a.screen_selector.showPopup()
        self.c.emergency = Mock()
        self.c.emergency.key_down.return_value = True
        QTest.keyPress(self.a.screen_selector.monitor_popup.rows[0], Qt.Key.Key_Escape)
        self.c.poll_escape()
        self.assertTrue(self.a.drawing)
        self.assertFalse(self.a.screen_selector.monitor_popup.isVisible())

    def test_first_annotation_uses_visible_controls_target_not_spotlight(self):
        primary = self.app.primaryScreen()
        other = self.other_screen()
        with patch.object(self.app, "screens", return_value=[primary, other]):
            self.c.selected_screen = other
            self.a.start()
            self.assertIs(self.a.screen, primary)
            self.assertEqual(self.a.screen_selector.currentData(), self.a.screen_key)

    def test_selector_moves_only_deliberately_and_cancel_preserves_history(self):
        primary = self.app.primaryScreen()
        other = self.other_screen()
        self.a.start()
        mark = Mark("pen", "#e53935", 4, 40, [QPointF(100, 120)])
        self.a.marks = [mark]
        self.a.history = [([], 1)]
        with patch.object(self.app, "screens", return_value=[primary, other]):
            self.a.sync_screen_controls()
            with patch("annotations.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel):
                self.a.screen_selector.setCurrentIndex(1)
            self.assertIs(self.a.screen, primary)
            self.assertEqual(self.a.screen_selector.currentIndex(), 0)
            with patch("annotations.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
                self.a.screen_selector.setCurrentIndex(1)
            self.assertIs(self.a.screen, other)
            self.assertEqual(self.a.overlay.geometry(), QRect(-1200, -100, 1200, 900))
            self.a.set_tool("arrow")
            self.a.interact()
            self.a.start()
            self.assertIs(self.a.screen, other)
            self.assertEqual(self.a.marks, [mark])
            self.a.undo()
            self.assertEqual(self.a.marks, [])

    def test_empty_selector_change_does_not_need_confirmation(self):
        primary = self.app.primaryScreen()
        other = self.other_screen()
        with patch.object(self.app, "screens", return_value=[primary, other]):
            self.a.sync_screen_controls()
            with patch("annotations.QMessageBox.question", side_effect=AssertionError("Empty marks need no confirmation")):
                self.a.screen_selector.setCurrentIndex(1)
            self.a.start()
            self.assertIs(self.a.screen, other)

    def test_wheel_over_focused_numeric_fields_does_not_change_values(self):
        self.c.panel.tabs.setCurrentIndex(1)
        for widget in (self.a.pen_width, self.a.highlighter_width, self.a.size,
                       self.a.shape_width, self.a.sequence, self.a.laser_size):
            with self.subTest(field=widget.accessibleName()):
                widget.setValue(20)
                widget.setFocus()
                wheel = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(), QPoint(0, -120),
                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                    Qt.ScrollPhase.NoScrollPhase, False)
                self.app.sendEvent(widget, wheel)
                self.assertEqual(widget.value(), 20)

    def test_default_highlighter_button_draws_horizontal(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.tool_buttons["highlighter"].click()
        QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(230, 170))
        self.assertEqual(self.a.marks[-1].tool, "horizontal_highlighter")
        self.assertEqual(self.a.marks[-1].points, [QPointF(100, 100), QPointF(230, 100)])


    def test_text_commits_multiline_moves_erases_and_restores_with_undo(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.set_tool("text")
        self.a.text_size.setValue(26)
        with patch("annotations.QInputDialog.getMultiLineText", return_value=("First line\nSecond line", True)):
            QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        self.assertEqual(len(self.a.marks), 1)
        mark = self.a.marks[0]
        self.assertEqual((mark.tool, mark.label, mark.size), ("text", "First line\nSecond line", 26))
        bounds = mark.path().boundingRect()
        self.assertGreater(bounds.height(), 40)
        self.assertTrue(mark.hit(bounds.center()))
        image = QImage(800, 800, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        mark.paint(painter)
        painter.end()
        self.assertTrue(any(image.pixelColor(x, y).alpha() for y in range(100, 170) for x in range(100, 300)))
        self.assertEqual(image.pixelColor(99, 99).alpha(), 0)
        self.a.set_tool("move")
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=bounds.center().toPoint())
        QTest.keyClick(self.a.overlay, Qt.Key.Key_Right)
        self.assertEqual(self.a.marks[0].points[0], QPointF(101, 100))
        self.a.undo()
        self.assertEqual(self.a.marks[0].points[0], QPointF(100, 100))
        self.a.set_tool("eraser")
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=bounds.center().toPoint())
        self.assertEqual(self.a.marks, [])
        self.a.undo()
        self.assertEqual(self.a.marks, [mark])
        self.a.undo()
        self.assertEqual(self.a.marks, [])
        self.a.redo()
        self.assertEqual(self.a.marks, [mark])

    def test_canceled_blank_and_disconnected_text_create_no_history(self):
        self.a.set_tool("text")
        for response in (("Canceled", False), (" \n ", True)):
            with patch("annotations.QInputDialog.getMultiLineText", return_value=response):
                self.a.add_text(QPointF(100, 100))
            self.assertEqual((self.a.marks, self.a.history), ([], []))
        def unplug(*args, **kwargs):
            self.a.sync_screen([])
            return ("Lost screen", True)
        with patch("annotations.QInputDialog.getMultiLineText", side_effect=unplug):
            self.a.add_text(QPointF(100, 100))
        self.assertEqual((self.a.marks, self.a.history), ([], []))
        self.assertFalse(self.a.text_entry_active)

    def test_text_near_edge_fits_monitor_and_too_long_text_is_rejected(self):
        self.a.set_tool("text")
        with patch("annotations.QInputDialog.getMultiLineText", return_value=("Near edge\nSecond line", True)):
            self.a.add_text(QPointF(790, 790))
        bounds = self.a.marks[0].path().boundingRect()
        self.assertLessEqual(bounds.right(), self.a.overlay.width())
        self.assertLessEqual(bounds.bottom(), self.a.overlay.height())
        with patch("annotations.QInputDialog.getMultiLineText", return_value=("line\n" * 1000, True)):
            self.a.add_text(QPointF(100, 100))
        self.assertEqual(len(self.a.marks), 1)
        self.assertEqual(len(self.a.history), 1)


    def test_fixed_capture_and_mode_controls_are_reachable_on_both_tabs(self):
        self.c.show_panel()
        for width, height in ((460, 680), (360, 480)):
            self.c.panel.resize(width, height)
            for index in (0, 1):
                self.c.panel.tabs.setCurrentIndex(index)
                self.app.processEvents()
                for control in (self.a.capture_button, self.a.save_button, self.a.draw_button, self.a.desktop_button):
                    self.assertTrue(control.isVisible())
                    pos = control.mapTo(self.c.panel, QPoint())
                    self.assertTrue(self.c.panel.rect().contains(QRect(pos, control.size())))
                    self.assertFalse(self.c.panel.tabs.isAncestorOf(control))
                before = self.a.capture_button.mapTo(self.c.panel, QPoint())
                scroll = self.c.panel.tabs.currentWidget()
                scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                self.assertEqual(self.a.capture_button.mapTo(self.c.panel, QPoint()), before)

    def test_global_toggle_retains_tool_monitor_and_marks_and_guards_modals(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.set_tool("arrow")
        target = self.a.screen
        self.a.marks = [Mark("pen", "#ff0000", 4, 40, [QPointF(30, 40)])]
        self.c.toggle_annotation_mode()
        self.assertFalse(self.a.drawing)
        self.c.toggle_annotation_mode()
        self.assertTrue(self.a.drawing)
        self.assertEqual(self.a.tool, "arrow")
        self.assertIs(self.a.screen, target)
        self.assertEqual(len(self.a.marks), 1)
        self.c.panel.tabs.setCurrentIndex(0)
        self.c.toggle_annotation_mode()
        self.assertEqual(self.c.panel.tabs.currentIndex(), 1)
        self.assertTrue(self.a.drawing)
        for attr in ("capturing", "text_entry_active"):
            setattr(self.a, attr, True)
            self.c.toggle_annotation_mode()
            self.assertTrue(self.a.drawing)
            setattr(self.a, attr, False)
        self.a.desktop_button.click()
        self.assertFalse(self.a.drawing)
        self.a.draw_button.click()
        self.assertTrue(self.a.drawing)

    def test_shared_capture_names_and_uses_explicit_monitor_on_both_tabs(self):
        primary = self.app.primaryScreen()
        other = self.other_screen()
        with patch.object(self.app, "screens", return_value=[primary, other]):
            self.a.bind_screen(other)
            for index in (0, 1):
                self.c.panel.tabs.setCurrentIndex(index)
                self.a.capture_scope.button(1).setChecked(True)
                self.a.sync_capture_scope()
                self.assertIn("Left monitor", self.a.capture_target.text())
                with patch("annotations.QTimer.singleShot") as timer, patch.object(self.a, "finish_capture") as finish:
                    self.a.capture()
                    self.c.toggle_annotation_mode()
                    self.assertFalse(self.a.drawing)
                    timer.call_args.args[1]()
                self.assertIs(finish.call_args.args[0], other)
                self.assertEqual(finish.call_args.args[1], QRect(-1200, -100, 1200, 900))
                self.a.capturing = False
                self.a.capture_button.setEnabled(True)
                self.a.save_button.setEnabled(True)

    def test_wheel_over_field_scrolls_panel_instead_of_changing_value(self):
        self.c.show_panel()
        self.c.panel.resize(460, 480)
        self.c.panel.tabs.setCurrentIndex(1)
        self.app.processEvents()
        scroll = self.c.panel.annotation_scroll
        scroll.ensureWidgetVisible(self.a.pen_width)
        old = scroll.verticalScrollBar().value()
        self.a.pen_width.setFocus()
        wheel = QWheelEvent(QPointF(10, 10), QPointF(self.a.pen_width.mapToGlobal(QPoint(10, 10))),
                            QPoint(), QPoint(0, -120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        self.app.sendEvent(self.a.pen_width, wheel)
        self.assertEqual(self.a.pen_width.value(), 4)
        self.assertGreater(scroll.verticalScrollBar().value(), old)


    def test_initial_panel_reaches_size_settings_without_scrolling(self):
        self.c.show_panel()
        self.c.panel.tabs.setCurrentIndex(1)
        self.app.processEvents()
        self.assertFalse(self.a.shape_width.visibleRegion().isEmpty())
        viewport = self.c.panel.annotation_scroll.viewport()
        point = self.a.shape_width.mapTo(viewport, self.a.shape_width.rect().bottomRight())
        self.assertTrue(viewport.rect().contains(point))


    def test_scrolling_monitor_selector_never_changes_monitor(self):
        primary = self.app.primaryScreen()
        other = self.other_screen()
        self.c.panel.tabs.setCurrentIndex(1)
        with patch.object(self.app, "screens", return_value=[primary, other]):
            self.a.sync_screen_controls()
            wheel = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(), QPoint(0, -120),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                Qt.ScrollPhase.NoScrollPhase, False)
            self.app.sendEvent(self.a.screen_selector, wheel)
            self.assertIs(self.a.screen, primary)
            self.assertEqual(self.a.screen_selector.currentIndex(), 0)

    def test_excess_text_reports_rejection_after_resuming_drawing(self):
        self.a.set_tool("text")
        with patch("annotations.QInputDialog.getMultiLineText", return_value=("line\n" * 1000, True)):
            self.a.add_text(QPointF(100, 100))
        self.assertTrue(self.a.drawing)
        self.assertIn("too large", self.a.status.text())

    @unittest.skipUnless(os.name == "nt", "Windows native hotkey dispatch")
    def test_native_spotlight_hotkeys_cannot_mutate_state_during_capture_or_text(self):
        import ctypes
        from ctypes import wintypes
        hotkeys = Hotkeys(self.c)
        hotkeys.registered = {1: self.c.select, 2: self.c.edit, 4: self.c.clear}
        self.c.selected_screen = self.app.primaryScreen()
        from PySide6.QtCore import QRectF
        self.c.focus = QRectF(100, 120, 200, 150)
        self.c.mode = "present"
        for attr in ("capturing", "text_entry_active"):
            setattr(self.a, attr, True)
            for ident in (1, 2, 4):
                message = wintypes.MSG()
                message.message = 0x0312
                message.wParam = ident
                hotkeys.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(message))
                self.app.processEvents()
                self.assertEqual(self.c.mode, "present")
                self.assertEqual(self.c.focus, QRectF(100, 120, 200, 150))
            setattr(self.a, attr, False)
        hotkeys.registered.clear()


    def test_show_controls_hotkey_waits_until_capture_pixels_are_grabbed(self):
        self.c.show_panel()
        hotkeys = Hotkeys(self.c)
        hotkeys.registered = {5: self.c.show_panel}
        with patch("annotations.QTimer.singleShot") as timer:
            self.a.capture()
            self.assertFalse(self.c.panel.isVisible())
            hotkeys.dispatch(5)
            self.assertFalse(self.c.panel.isVisible(), "Controls must not reappear in the capture")
            self.assertTrue(self.a.capturing)
            callback = timer.call_args.args[1]
        with patch.object(self.a.screen or self.c.panel.screen(), "grabWindow") as grab:
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(800, 800)
            pixmap.fill(QColor("white"))
            grab.return_value = pixmap
            callback()
        self.assertFalse(self.a.capturing)
        self.assertTrue(self.c.panel.isVisible())
        hotkeys.registered.clear()


    def test_text_tool_has_readable_icon_before_and_after_activation(self):
        self.c.panel.tabs.setCurrentIndex(1)
        button = self.a.tool_buttons["text"]
        self.assertFalse(button.icon().isNull(), "Text needs its ABC icon before activation")
        button.click()
        self.assertEqual(self.a.tool, "text")
        self.assertTrue(self.a.drawing)
        self.assertFalse(button.icon().isNull(), "Selecting Text must retain its icon")
        self.assertEqual(button.accessibleName(), "Text")
        self.assertEqual(button.text(), "", "ABC artwork replaces the plain Text label")
