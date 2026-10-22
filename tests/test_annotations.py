import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from annotations import Mark, PALETTES, marker_label
from spotlight import Spotlight


class AnnotationTests(unittest.TestCase):
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

    def test_sizes_can_be_set_without_switching_tools_and_tooltips_work_inactive(self):
        self.c.panel.tabs.setCurrentIndex(1)
        for widget in (self.a.pen_width, self.a.highlighter_width, self.a.size):
            self.assertTrue(widget.isVisible())
        self.a.highlighter_width.setValue(32)
        self.a.size.setValue(60)
        self.a.pen_width.setValue(2)
        self.a.set_tool("highlighter")
        self.assertEqual(self.a.width.value(), 32)
        self.a.set_tool("pen")
        self.assertEqual(self.a.width.value(), 2)
        self.a.set_tool("number")
        self.assertEqual(self.a.size.value(), 60)
        self.assertTrue(self.c.panel.testAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips))
        for button in self.a.tool_buttons.values():
            self.assertIn(":", button.toolTip())

    def test_slim_numbers_support_buttons_typing_and_bounds(self):
        self.c.panel.tabs.setCurrentIndex(1)
        for widget in (self.a.pen_width, self.a.highlighter_width, self.a.size, self.a.shape_width):
            widget.setValue(widget.minimum())
            widget.down_arrow.click()
            self.assertEqual(widget.value(), widget.minimum())
            widget.up_arrow.click()
            self.assertEqual(widget.value(), widget.minimum() + 1)
            widget.lineEdit().setText(str(widget.maximum()))
            widget.interpretText()
            widget.up_arrow.click()
            self.assertEqual(widget.value(), widget.maximum())
        self.a.set_tool("letter")
        self.a.sequence.setValue(26)
        self.a.sequence.up_arrow.click()
        self.assertEqual(self.a.sequence.text(), "AA")

    def test_desktop_mode_toggle_and_every_tool_have_one_selected_button(self):
        self.c.show_panel()
        self.c.panel.tabs.setCurrentIndex(1)
        for tool in self.a.tool_specs:
            with self.subTest(tool=tool):
                self.a.set_tool(tool)
                self.assertTrue(self.a.drawing)
                self.assertEqual([b for b in self.a.tools.buttons() if b.isChecked()],
                                 [self.a.tool_buttons[tool]])
                self.a.interact_button.click()
                self.assertFalse(self.a.drawing)
                self.assertEqual([b for b in self.a.tools.buttons() if b.isChecked()],
                                 [self.a.interact_button])
                self.a.interact_button.click()
                self.assertTrue(self.a.drawing)
                self.assertEqual(self.a.tool, tool)
                self.assertEqual([b for b in self.a.tools.buttons() if b.isChecked()],
                                 [self.a.tool_buttons[tool]])
                self.a.interact()
                self.a.tool_buttons[tool].click()
                self.assertTrue(self.a.drawing)
                self.assertEqual(self.a.tool, tool)
        self.c.panel.tabs.setCurrentIndex(0)
        self.assertEqual(self.a.tools.checkedButton(), self.a.interact_button)

    def test_manual_typing_commits_all_sizes_and_marker_values(self):
        self.c.show_panel()
        self.c.panel.tabs.setCurrentIndex(1)
        for tool, widget, text, expected in (
                ("pen", self.a.pen_width, "12", 12),
                ("highlighter", self.a.highlighter_width, "30", 30),
                ("rectangle", self.a.shape_width, "9", 9),
                ("number", self.a.size, "85", 85),
                ("laser", self.a.laser_size, "28", 28),
                ("number", self.a.sequence, "123456", 123456),
                ("letter", self.a.sequence, "AZ", 52)):
            with self.subTest(tool=tool, field=widget.accessibleName()):
                self.a.set_tool(tool)
                self.c.panel.annotation_scroll.ensureWidgetVisible(widget)
                self.app.processEvents()
                QTest.mouseClick(widget.lineEdit(), Qt.MouseButton.LeftButton)
                QTest.keyClick(widget.lineEdit(), Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
                QTest.keyClicks(widget.lineEdit(), text)
                QTest.keyClick(widget.lineEdit(), Qt.Key.Key_Return)
                self.assertEqual(widget.value(), expected)
                self.assertTrue(self.a.drawing, "Editing values must not end drawing")
        self.assertEqual(self.a.sequence.text(), "AZ")

    def test_tool_shortcuts_activate_and_tooltips_match(self):
        from annotations import TOOL_SHORTCUTS
        self.c.show_panel()
        self.c.panel.tabs.setCurrentIndex(1)
        self.app.processEvents()
        self.c.panel.activateWindow()
        self.c.panel.setFocus()
        QTest.qWait(20)
        modifiers = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
        for key, tool in ((Qt.Key.Key_A, "arrow"), (Qt.Key.Key_P, "pen")):
            QTest.keyClick(self.c.panel, key, modifiers)
            self.assertEqual(self.a.tool, tool)
            self.assertTrue(self.a.drawing)
        QTest.keyClick(self.c.panel, Qt.Key.Key_N, modifiers | Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.a.tool, "letter")
        self.c.panel.tabs.setCurrentIndex(0)
        self.c.panel.activateWindow()
        self.c.panel.setFocus()
        QTest.keyClick(self.c.panel, Qt.Key.Key_A, modifiers)
        self.assertEqual(self.a.tool, "letter", "Hidden annotation shortcuts must not change tools")
        self.c.panel.tabs.setCurrentIndex(1)
        for tool, (label, _) in self.a.tool_specs.items():
            self.a.set_tool(tool)
            self.assertIn(TOOL_SHORTCUTS[label], self.a.tool_buttons[tool].toolTip())
        self.a.interact_button.click()
        self.assertIn("Ctrl+Alt+D", self.a.interact_button.toolTip())

    def test_fast_color_switch_and_palette_animation_end_at_current_selection(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.app.processEvents()
        for index in (2, 4, 6):
            self.a.swatches.button(index).click()
            self.assertEqual(self.a.color, index)
        track = self.a.swatch_track
        track.slide.setCurrentTime(track.slide.duration())
        expected = QRectF(self.a.swatches.button(6).geometry()).adjusted(-1, -1, 1, 1)
        self.assertEqual(track.outline, expected)
        self.a.variant.button(1).click()
        for i, button in enumerate(self.a.swatches.buttons()):
            button.fade.setCurrentTime(button.fade.duration())
            self.assertEqual(button.color, QColor(PALETTES[1][i]))
        self.assertEqual(self.a.swatches.checkedId(), 6)
        self.assertEqual(self.a.swatches.button(6).accessibleName(), "Purple")

    def test_sequence_labels(self):
        self.assertEqual([marker_label(n, True) for n in (1, 26, 27, 52, 53, 702, 703)],
                         ["A", "Z", "AA", "AZ", "BA", "ZZ", "AAA"])

    def test_pen_and_highlighter_keep_independent_widths_in_strokes(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.assertEqual(self.a.width.value(), 4)
        self.a.width.setValue(3)
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        self.a.set_tool("highlighter")
        self.assertEqual(self.a.width.value(), 20)
        self.a.width.setValue(28)
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 150))
        self.a.set_tool("pen")
        self.assertEqual(self.a.width.value(), 3)
        self.a.set_tool("highlighter")
        self.assertEqual(self.a.width.value(), 28)
        self.assertEqual([mark.width for mark in self.a.marks], [3, 28])

    def test_annotation_tab_immediately_activates_current_tool(self):
        self.c.selected_screen = self.app.primaryScreen()
        self.c.focus = QRectF(100, 100, 200, 200)
        self.c.edit()
        self.c.panel.tabs.setCurrentIndex(1)
        self.assertTrue(self.a.drawing)
        self.assertEqual(self.a.tool, "pen")
        self.assertEqual(self.c.mode, "present")
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(140, 140))
        self.assertEqual(len(self.a.marks), 1)
        self.a.set_tool("highlighter")
        self.c.panel.tabs.setCurrentIndex(0)
        self.assertFalse(self.a.drawing)
        self.c.panel.tabs.setCurrentIndex(1)
        self.assertTrue(self.a.drawing)
        self.assertEqual(self.a.tool, "highlighter")

    def test_letter_field_displays_and_accepts_letters(self):
        self.a.set_tool("letter")
        self.a.sequence.setValue(8)
        self.assertEqual(self.a.sequence.text(), "H")
        self.a.sequence.setValue(26)
        self.a.sequence.stepUp()
        self.assertEqual(self.a.sequence.text(), "AA")
        self.a.sequence.lineEdit().setText("AB")
        self.a.sequence.interpretText()
        self.assertEqual(self.a.sequence.value(), 28)
        self.a.set_tool("number")
        self.assertEqual(self.a.sequence.text(), "28")

    def test_controls_return_after_area_selection_and_tabs_fill_row(self):
        self.c.select()
        overlay = self.c.overlays[0]
        QTest.mousePress(overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        QTest.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
        self.app.processEvents()
        self.assertEqual(self.c.mode, "edit")
        self.assertFalse(self.c.panel.isMinimized())
        self.assertTrue(self.c.panel.isVisible())
        point = overlay.mapFromGlobal(self.c.panel.mapToGlobal(QPoint(20, 20)))
        self.assertFalse(overlay.mask().contains(point))
        tabs = self.c.panel.tabs
        self.assertEqual(tabs.tabBar().width(), tabs.width())
        self.assertLessEqual(abs(tabs.tabBar().tabRect(0).width() - tabs.tabBar().tabRect(1).width()), 1)

    def test_markers_retain_color_and_undo_sequence(self):
        self.a.start()
        self.a.set_tool("letter")
        self.a.sequence.setValue(26)
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        self.a.variant.button(1).click()
        self.a.set_color(5)
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(200, 100))
        self.assertEqual([m.label for m in self.a.marks], ["Z", "AA"])
        self.assertEqual([m.color for m in self.a.marks], [PALETTES[0][0], PALETTES[1][5]])
        self.a.undo()
        self.assertEqual(self.a.sequence.value(), 27)
        self.a.redo()
        self.assertEqual(self.a.sequence.value(), 28)
        self.a.clear()
        self.assertFalse(self.a.marks)
        self.a.undo()
        self.assertEqual(len(self.a.marks), 2)

    def test_pen_release_endpoint_and_object_eraser(self):
        self.a.start()
        QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(80, 80))
        QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(160, 80))
        self.assertEqual(self.a.marks[0].points[-1], QPointF(160, 80))
        self.a.set_tool("eraser")
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(120, 80))
        self.assertFalse(self.a.marks)
        self.a.undo()
        self.assertEqual(len(self.a.marks), 1)

    def test_escape_keeps_spotlight_and_ink_and_clicks_pass_through(self):
        self.c.selected_screen = self.app.primaryScreen()
        self.c.focus = QRectF(100, 100, 200, 200)
        self.a.start()
        self.a.set_tool("number")
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(140, 140))
        self.c.escape()
        self.assertFalse(self.a.drawing)
        self.assertEqual(self.c.mode, "present")
        self.assertEqual(len(self.a.marks), 1)
        self.assertTrue(self.a.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.c.clear()
        self.assertEqual(len(self.a.marks), 1)

    def test_duplicate_escape_dispatch_does_not_clear_spotlight(self):
        self.c.selected_screen = self.app.primaryScreen()
        self.c.focus = QRectF(100, 100, 200, 200)
        self.a.start()
        self.c.emergency = Mock()
        self.c.emergency.key_down.return_value = True
        self.c.escape()
        self.c.poll_escape()
        self.c.escape()
        self.assertEqual(self.c.mode, "present")
        self.c.emergency.key_down.return_value = False
        self.c.poll_escape()
        self.c.emergency.key_down.return_value = True
        self.c.escape()
        self.assertEqual(self.c.mode, "off")

    def test_marker_and_highlighter_render_and_shape_hit(self):
        image = QImage(200, 200, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        Mark("highlighter", "#ff0000", 20, 40, [QPointF(20, 20), QPointF(100, 20)]).paint(painter)
        Mark("number", "#00ff00", 4, 40, [QPointF(100, 100)], "1").paint(painter)
        painter.end()
        self.assertEqual(image.pixelColor(50, 20).alpha(), 90)
        self.assertEqual(image.pixelColor(90, 100).green(), 255)
        rect = Mark("rectangle", "#ff0000", 4, 40, [QPointF(10, 10), QPointF(60, 60)])
        self.assertTrue(rect.hit(QPointF(10, 30)))
        self.assertFalse(rect.hit(QPointF(35, 35)))

    def test_capture_crop_uses_monitor_origin_and_pixel_ratio(self):
        screen = Mock()
        screen.geometry.return_value = QRect(-500, 0, 500, 400)
        pixmap = QPixmap(1000, 800)
        pixmap.fill(QColor("#11aa33"))
        pixmap.setDevicePixelRatio(2)
        screen.grabWindow.return_value = pixmap
        with patch.object(self.c.app, "screens", return_value=[screen]):
            self.a.finish_capture(screen, QRectF(-450, 30, 120, 80))
        self.assertEqual(self.a.captured.size().width(), 240)
        self.assertEqual(self.a.captured.size().height(), 160)
        self.assertTrue(self.a.capture_button.isEnabled())

    def test_capture_defaults_to_selection_with_monitor_fallback(self):
        self.c.selected_screen = self.app.primaryScreen()
        self.c.focus = QRectF(100, 100, 200, 150)
        with patch("annotations.QTimer.singleShot") as timer, patch.object(self.a, "finish_capture") as finish:
            self.a.capture()
            self.assertFalse(self.c.panel.isVisible())
            timer.call_args.args[1]()
            self.assertEqual(finish.call_args.args[1], QRectF(100, 100, 200, 150))
            self.a.capturing = False  # The mocked completion does not release the capture guard.
            self.c.clear()
            self.a.capture()
            timer.call_args.args[1]()
            screen = finish.call_args.args[0]
            self.assertEqual(finish.call_args.args[1], QRectF(screen.geometry()))

    def test_removed_monitor_reset_does_not_access_dead_screen(self):
        self.a.screen = Mock()
        self.a.screen.geometry.side_effect = RuntimeError("Screen was deleted")
        self.a.drawing = True
        self.a.reset_screen()
        self.assertIsNone(self.a.screen)
        self.assertFalse(self.a.drawing)
        self.assertFalse(self.a.overlay.isVisible())

    def test_tool_click_starts_drawing_and_keeps_controls_available(self):
        self.c.selected_screen = self.app.primaryScreen()
        self.c.focus = QRectF(100, 100, 200, 200)
        self.c.edit()
        self.c.show_panel()
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.tool_buttons["highlighter"].click()
        self.assertTrue(self.a.drawing)
        self.assertEqual(self.c.mode, "present")
        self.assertFalse(self.c.panel.isMinimized())
        self.assertTrue(self.c.panel.isVisible())
        self.assertEqual(self.c.panel.status.text(), "Highlighter active")
        panel_point = self.a.overlay.mapFromGlobal(self.c.panel.mapToGlobal(QPoint(30, 30)))
        self.assertFalse(self.a.overlay.mask().contains(panel_point))
        self.c.panel.move(300, 100)
        self.app.processEvents()
        panel_point = self.a.overlay.mapFromGlobal(self.c.panel.mapToGlobal(QPoint(30, 30)))
        self.assertFalse(self.a.overlay.mask().contains(panel_point))
        self.a.tool_buttons["number"].click()
        self.assertTrue(self.a.drawing)
        self.assertTrue(self.a.pen_width.isVisible())
        self.assertTrue(self.a.highlighter_width.isVisible())
        self.assertTrue(self.a.size.isVisible())
        self.c.show_panel()
        self.assertTrue(self.a.drawing)
        self.c.panel.tabs.setCurrentIndex(0)
        self.assertFalse(self.a.drawing)

    def test_capture_radio_availability_and_explicit_full_monitor(self):
        self.a.sync_capture_scope()
        self.assertFalse(self.a.capture_scope.button(0).isEnabled())
        self.assertEqual(self.a.capture_scope.checkedId(), 1)
        self.c.focus = QRectF(100, 100, 200, 200)
        self.a.sync_capture_scope()
        self.assertEqual(self.a.capture_scope.checkedId(), 0)
        self.a.capture_scope.button(1).click()
        self.a.sync_capture_scope()
        self.assertEqual(self.a.capture_scope.checkedId(), 1)
        self.c.focus = QRectF()
        self.a.sync_capture_scope()
        self.assertFalse(self.a.capture_scope.button(0).isEnabled())


    def test_horizontal_highlighter_and_shift_vertical_with_reverse_drags(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.tool_actions["horizontal_highlighter"].trigger()
        self.a.highlighter_width.setValue(30)
        for modifiers, end, expected in (
            (Qt.KeyboardModifier.NoModifier, QPoint(80, 190), QPointF(80, 100)),
            (Qt.KeyboardModifier.ShiftModifier, QPoint(80, 190), QPointF(150, 190)),
        ):
            QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton, modifiers, QPoint(150, 100))
            QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton, modifiers, end)
            self.assertEqual(self.a.marks[-1].points, [QPointF(150, 100), expected])
            self.assertEqual(self.a.marks[-1].width, 30)
        image = QImage(200, 220, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        self.a.marks[0].paint(painter)
        painter.end()
        self.assertEqual(image.pixelColor(110, 100).alpha(), 90)
        self.assertEqual(image.pixelColor(110, 150).alpha(), 0)

    def test_filled_shapes_use_palette_erase_interior_and_undo(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.variant.button(1).click()
        self.a.set_color(5)
        for tool in ("filled_rectangle", "filled_circle"):
            self.a.set_tool(tool)
            QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(180, 180))
            QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(80, 60))
            mark = self.a.marks[-1]
            self.assertEqual(mark.color, PALETTES[1][5])
            image = QImage(220, 220, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            mark.paint(painter)
            painter.end()
            self.assertEqual(image.pixelColor(130, 130), QColor(PALETTES[1][5]))
            if tool == "filled_circle":
                bounds = mark.path().boundingRect()
                self.assertEqual(bounds.width(), bounds.height())
            count = len(self.a.marks)
            self.a.set_tool("eraser")
            QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(130, 130))
            self.assertEqual(len(self.a.marks), count - 1)
            self.a.undo()
            self.assertEqual(len(self.a.marks), count)
            self.a.redo()
            self.assertEqual(len(self.a.marks), count - 1)

    def test_shift_rectangles_make_squares(self):
        self.c.panel.tabs.setCurrentIndex(1)
        for tool in ("rectangle", "filled_rectangle"):
            self.a.set_tool(tool)
            QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.ShiftModifier, QPoint(180, 180))
            QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton,
                               Qt.KeyboardModifier.ShiftModifier, QPoint(80, 60))
            self.assertEqual(self.a.marks[-1].points[-1], QPointF(80, 80))

    def test_group_menu_has_icons_and_remembers_chosen_variant(self):
        self.c.panel.tabs.setCurrentIndex(1)
        for primary, variant in (("highlighter", "horizontal_highlighter"),
                                 ("rectangle", "filled_rectangle"), ("circle", "filled_circle"),
                                 ("number", "letter")):
            button = self.a.tool_buttons[primary]
            QTest.mouseClick(button, Qt.MouseButton.RightButton)
            self.assertTrue(button.tool_menu.isVisible())
            for action in button.tool_menu.actions():
                self.assertFalse(action.icon().isNull())
                self.assertTrue(action.text())
            button.tool_menu.hide()
            self.a.tool_actions[variant].trigger()
            self.assertEqual(self.a.tool, variant)
            self.assertEqual(button.accessibleName(), self.a.tool_specs[variant][0])
            self.a.set_tool("pen")
            button.click()
            self.assertEqual(self.a.tool, variant)
            self.assertTrue(self.a.tool_actions[variant].isChecked())
        button = self.a.tool_buttons["highlighter"]
        QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=QPoint(button.width() - 10, 18))
        self.assertTrue(button.tool_menu.isVisible())
        button.tool_menu.hide()
        QTest.keyClick(button, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
        self.assertTrue(button.tool_menu.isVisible())
        button.tool_menu.hide()

    def test_laser_is_temporary_click_through_and_restores_drawing_input(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.size.setValue(54)
        self.c.panel.move(300, 200)
        self.app.processEvents()
        self.a.set_tool("laser")
        self.a.laser_size.setValue(32)
        self.assertTrue(self.a.laser_size.isVisible())
        self.assertFalse(self.a.size.isVisible())
        self.assertTrue(self.a.overlay.laser_timer.isActive())
        self.assertTrue(self.a.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        global_point = self.a.overlay.mapToGlobal(QPoint(100, 100))
        with patch("annotations.QCursor.pos", return_value=global_point):
            self.a.overlay.track_laser()
        self.assertEqual(self.a.overlay.laser_point, QPointF(100, 100))
        self.a.set_color(5)
        image = QImage(220, 220, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        self.a.overlay.paint_laser(painter)
        painter.end()
        self.assertGreater(image.pixelColor(110, 100).blue(), image.pixelColor(110, 100).red())
        self.assertGreater(image.pixelColor(110, 100).alpha(), 0)
        self.assertEqual(image.pixelColor(140, 100).alpha(), 0)
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        self.assertFalse(self.a.marks)
        self.assertFalse(self.a.history)
        self.a.set_tool("pen")
        self.assertIsNone(self.a.overlay.laser_point)
        self.assertFalse(self.a.overlay.laser_timer.isActive())
        self.assertFalse(self.a.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.assertEqual(self.a.size.value(), 54)
        self.a.set_tool("laser")
        self.assertEqual(self.a.laser_size.value(), 32)
        self.c.escape()
        self.assertFalse(self.a.drawing)
        self.assertFalse(self.a.overlay.laser_timer.isActive())
        self.assertIsNone(self.a.overlay.laser_point)

    def test_capture_image_always_copies_fresh_pixels(self):
        screen = self.app.primaryScreen()
        old = QPixmap(40, 40)
        old.fill(QColor("red"))
        fresh = QPixmap(screen.geometry().size())
        fresh.fill(QColor("#11aa33"))
        self.a.captured = old
        self.app.clipboard().setPixmap(old)
        with patch("annotations.QTimer.singleShot") as timer, patch.object(type(screen), "grabWindow", return_value=fresh):
            self.a.capture_button.click()
            self.assertTrue(self.a.capturing)
            self.assertFalse(self.c.panel.isVisible())
            self.assertFalse(self.a.capture_button.isEnabled())
            self.a.capture()
            self.assertEqual(timer.call_count, 1)
            timer.call_args.args[1]()
        self.assertEqual(self.app.clipboard().pixmap().toImage().pixelColor(10, 10), QColor("#11aa33"))
        self.assertEqual(self.a.status.text(), "Copied to clipboard")
        self.assertFalse(self.a.capturing)
        self.assertTrue(self.c.panel.isVisible())
        self.assertTrue(self.a.capture_button.isEnabled())
        self.assertTrue(self.a.save_button.isEnabled())

    def test_failed_capture_keeps_clipboard_and_restores_controls(self):
        old = QPixmap(40, 40)
        old.fill(QColor("red"))
        self.app.clipboard().setPixmap(old)
        screen = self.app.primaryScreen()
        with patch("annotations.QTimer.singleShot") as timer, patch.object(type(screen), "grabWindow", return_value=QPixmap()):
            self.a.capture_button.click()
            timer.call_args.args[1]()
        self.assertEqual(self.app.clipboard().pixmap().toImage().pixelColor(10, 10), QColor("red"))
        self.assertIn("unavailable", self.a.status.text())
        self.assertTrue(self.a.capture_button.isEnabled())
        self.assertTrue(self.a.save_button.isEnabled())
        self.assertFalse(self.a.capturing)
        self.assertTrue(self.c.panel.isVisible())


    def test_move_all_annotation_types_keeps_originals_and_one_undo_step(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.set_tool("move")
        for tool in ("pen", "highlighter", "horizontal_highlighter", "arrow", "rectangle", "circle",
                     "filled_rectangle", "filled_circle", "number", "letter"):
            with self.subTest(tool=tool):
                points = ([QPointF(125, 125)] if tool in ("number", "letter") else
                          [QPointF(100, 125), QPointF(160, 125)] if tool == "horizontal_highlighter" else
                          [QPointF(100, 100), QPointF(160, 160)])
                mark = Mark(tool, "#e53935", 4, 40, points, "A" if tool == "letter" else "1" if tool == "number" else "")
                self.a.marks = [mark]
                self.a.history.clear()
                self.a.future.clear()
                self.a.sequence.setValue(27)
                QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(125, 125))
                QTest.mouseMove(self.a.overlay, QPoint(145, 135))
                QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(165, 155))
                moved = [point + QPointF(40, 30) for point in points]
                self.assertEqual(self.a.marks[0].points, moved)
                self.assertEqual(mark.points, points, "Moving mutated the undo snapshot")
                self.assertEqual(len(self.a.history), 1)
                self.assertEqual(self.a.marks[0].label, mark.label)
                self.a.undo()
                self.assertEqual(self.a.marks[0].points, points)
                self.assertEqual(self.a.sequence.value(), 27)
                self.a.redo()
                self.assertEqual(self.a.marks[0].points, moved)

    def test_move_topmost_shape_by_interior_clamps_and_supports_arrows(self):
        self.c.panel.tabs.setCurrentIndex(1)
        first = Mark("rectangle", "#e53935", 4, 40, [QPointF(100, 100), QPointF(180, 180)])
        top = Mark("circle", "#3265e8", 4, 40, [QPointF(110, 110), QPointF(170, 170)])
        self.a.marks = [first, top]
        self.a.set_tool("move")
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(140, 140))
        self.assertEqual(self.a.overlay.selected_index, 1)
        self.assertFalse(self.a.history, "Selection alone created an undo entry")
        QTest.keyClick(self.a.overlay, Qt.Key.Key_Right)
        QTest.keyClick(self.a.overlay, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.a.marks[1].points[0], QPointF(111, 100))
        self.assertEqual(self.a.marks[0].points, first.points)
        QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(141, 130))
        QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(-400, -400))
        bounds = self.a.marks[1].path().boundingRect()
        self.assertEqual(bounds.topLeft(), QPointF(0, 0))
        self.a.undo()
        self.assertEqual(self.a.marks[1].points[0], QPointF(111, 100))
        self.assertIsNone(self.a.overlay.selected_index)

    def test_move_empty_click_does_not_draw_and_tool_switch_deselects(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.a.marks = [Mark("filled_rectangle", "#e53935", 4, 40, [QPointF(100, 100), QPointF(180, 180)])]
        self.a.tool_buttons["move"].click()
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(140, 140))
        self.assertEqual(self.a.overlay.selected_index, 0)
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(250, 250))
        self.assertIsNone(self.a.overlay.selected_index)
        self.assertEqual(len(self.a.marks), 1)
        self.assertFalse(self.a.history)
        QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(140, 140))
        self.a.set_tool("pen")
        self.assertIsNone(self.a.overlay.selected_index)

    def test_laser_cursor_restores_over_controls_and_after_stop(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.c.panel.move(300, 200)
        self.app.processEvents()
        self.c.system_cursor = Mock()
        self.a.set_tool("laser")
        with patch("annotations.QCursor.pos", return_value=self.a.overlay.mapToGlobal(QPoint(100, 100))):
            self.a.overlay.track_laser()
        self.c.system_cursor.set_hidden.assert_called_with(True)
        over_controls = self.c.panel.mapToGlobal(QPoint(30, 30))
        with patch("annotations.QCursor.pos", return_value=over_controls):
            self.a.overlay.track_laser()
        self.c.system_cursor.set_hidden.assert_called_with(False)
        self.assertIsNone(self.a.overlay.laser_point)
        self.a.interact()
        self.c.system_cursor.restore.assert_called()


    def test_tabs_and_tools_keep_one_control_window_size(self):
        self.c.show_panel()
        self.app.processEvents()
        expected = self.c.panel.geometry()
        footer = self.c.panel.version_label.geometry()
        for tool in ("pen", "letter", "number", "laser", "filled_rectangle", "move"):
            self.c.panel.tabs.setCurrentIndex(1)
            self.a.set_tool(tool)
            self.app.processEvents()
            self.assertEqual(self.c.panel.geometry(), expected, tool)
            self.assertEqual(self.c.panel.version_label.geometry(), footer, tool)
            self.c.panel.tabs.setCurrentIndex(0)
            self.app.processEvents()
            self.assertEqual(self.c.panel.geometry(), expected, tool)
            self.assertEqual(self.c.panel.version_label.geometry(), footer, tool)

    def test_last_swatch_is_black_in_both_palettes_and_draws_black(self):
        self.c.panel.tabs.setCurrentIndex(1)
        self.assertEqual(len(self.a.swatches.buttons()), 8)
        black = self.a.swatches.button(7)
        self.assertEqual(black.accessibleName(), "Black")
        for variant in (0, 1):
            self.a.variant.button(variant).click()
            black.click()
            black.fade.setCurrentTime(black.fade.duration())
            self.assertEqual(black.color, QColor("#212121"))
            self.a.set_tool("filled_rectangle")
            QTest.mousePress(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(80, 80))
            QTest.mouseRelease(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(140, 140))
            self.assertEqual(self.a.marks[-1].color, "#212121")
            image = QImage(180, 180, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            self.a.marks[-1].paint(painter)
            painter.end()
            self.assertEqual(image.pixelColor(110, 110), QColor("#212121"))
        self.a.set_tool("laser")
        self.a.overlay.laser_point = QPointF(90, 90)
        image = QImage(180, 180, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        self.a.overlay.paint_laser(painter)
        painter.end()
        color = image.pixelColor(97, 90)
        self.assertLess(color.red(), 70)
        self.assertEqual(color.red(), color.green())
        self.assertEqual(color.green(), color.blue())


    def other_screen(self, name="Other monitor", bounds=QRect(-1000, -200, 900, 700)):
        screen = Mock()
        screen.name.return_value = name
        screen.serialNumber.return_value = name + " serial"
        screen.manufacturer.return_value = "Test"
        screen.model.return_value = "Monitor"
        screen.geometry.return_value = bounds
        return screen

    def seed_screen_history(self):
        self.c.panel.tabs.setCurrentIndex(1)
        first = Mark("pen", "#e53935", 4, 40, [QPointF(100, 100), QPointF(180, 100)])
        second = Mark("number", "#3265e8", 4, 40, [QPointF(700, 700)], "8")
        self.a.marks = [first, second]
        self.a.history = [([first], 8)]
        self.a.future = [([first, second], 10)]
        self.a.sequence.setValue(9)
        return list(self.a.marks), list(self.a.history), list(self.a.future)

    def assert_screen_history(self, snapshot):
        self.assertEqual((self.a.marks, self.a.history, self.a.future), snapshot)
        self.assertEqual(self.a.sequence.value(), 9)

    def test_controls_and_spotlight_screen_changes_do_not_repin_or_delete_ink(self):
        snapshot = self.seed_screen_history()
        pinned = self.a.screen
        bounds = self.a.overlay.geometry()
        other = self.other_screen()
        with patch.object(self.app, "screens", return_value=[pinned, other]), patch.object(type(self.c.panel), "screen", return_value=other):
            self.c.selected_screen = other
            self.c.focus = QRectF(-900, 0, 200, 200)
            self.c.mode = "present"
            self.a.set_tool("highlighter")
            self.a.set_tool("move")
            QTest.mouseClick(self.a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(140, 100))
            self.assertEqual(self.a.overlay.selected_index, 0)
            self.a.interact()
            self.a.start()
            self.c.panel.tabs.setCurrentIndex(0)
            self.c.panel.tabs.setCurrentIndex(1)
            self.c.geometry_changed()
            self.assertTrue(self.a.move_screen_button.isEnabled())
            self.assertIs(self.a.screen, pinned)
            self.assertEqual(self.a.overlay.geometry(), bounds)
            self.assert_screen_history(snapshot)

    def test_changed_annotation_bounds_keep_all_ink_and_undo_snapshots(self):
        snapshot = self.seed_screen_history()
        screen = self.a.screen
        original = screen.geometry()
        smaller = QRect(-500, 40, 400, 300)
        with patch.object(type(screen), "geometry", return_value=smaller):
            self.c.geometry_changed()
            self.assertEqual(self.a.overlay.geometry(), smaller)
            self.assertTrue(self.a.drawing)
            self.assert_screen_history(snapshot)
        self.c.geometry_changed()
        self.assertEqual(self.a.overlay.geometry(), original)
        self.assert_screen_history(snapshot)
        self.a.undo()
        self.assertEqual(len(self.a.marks), 1)
        self.assertEqual(self.a.sequence.value(), 8)
        self.a.redo()
        self.assertEqual(self.a.marks, snapshot[0])

    def test_disconnected_annotation_screen_keeps_ink_without_falling_back(self):
        snapshot = self.seed_screen_history()
        pinned = self.a.screen
        other = self.other_screen()
        with patch.object(self.app, "screens", return_value=[other]), patch.object(type(pinned), "geometry", side_effect=RuntimeError("Deleted screen")), patch.object(type(self.c.panel), "screen", return_value=other):
            self.c.geometry_changed()
            self.assertIsNone(self.a.screen)
            self.assertFalse(self.a.drawing)
            self.assertFalse(self.a.overlay.isVisible())
            self.a.set_tool("pen")
            self.assertIsNone(self.a.screen)
            self.assertIn("disconnected", self.a.status.text())
            self.assertTrue(self.a.move_screen_button.isEnabled())
            self.assert_screen_history(snapshot)

    def test_same_monitor_reconnects_and_restores_retained_marks(self):
        snapshot = self.seed_screen_history()
        original = self.a.screen
        replacement = self.other_screen()
        replacement.name.return_value, replacement.serialNumber.return_value, replacement.manufacturer.return_value, replacement.model.return_value = self.a.screen_key
        self.a.sync_screen([])
        with patch.object(self.app, "screens", return_value=[replacement]):
            self.a.sync_screen()
            self.assertIs(self.a.screen, replacement)
            self.assertIsNot(self.a.screen, original)
            self.assertTrue(self.a.overlay.isVisible())
            self.assertFalse(self.a.drawing)
            self.assert_screen_history(snapshot)

    def test_removing_spotlight_monitor_preserves_annotations_on_other_monitor(self):
        snapshot = self.seed_screen_history()
        pinned = self.a.screen
        self.c.selected_screen = self.other_screen()
        self.c.focus = QRectF(-900, 0, 200, 200)
        self.c.mode = "present"
        self.c.geometry_changed()
        self.assertTrue(self.c.focus.isEmpty())
        self.assertIs(self.a.screen, pinned)
        self.assertTrue(self.a.overlay.isVisible())
        self.assert_screen_history(snapshot)

    def test_explicit_screen_move_requires_confirmation_and_preserves_history(self):
        snapshot = self.seed_screen_history()
        pinned = self.a.screen
        other = self.other_screen()
        with patch.object(self.app, "screens", return_value=[pinned, other]), patch.object(type(self.c.panel), "screen", return_value=other), patch("annotations.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel) as question:
            self.a.move_screen_button.setEnabled(True)
            self.a.move_screen_button.click()
            question.assert_called_once()
            self.assertIs(self.a.screen, pinned)
            self.assertTrue(self.a.drawing)
            self.assert_screen_history(snapshot)
            question.return_value = QMessageBox.StandardButton.Yes
            self.a.move_screen_button.click()
            self.assertIs(self.a.screen, other)
            self.assertEqual(self.a.overlay.geometry(), other.geometry())
            self.assertTrue(self.a.drawing)
            self.assert_screen_history(snapshot)
            self.a.undo()
            self.assertEqual(len(self.a.marks), 1)
            self.a.redo()
            self.assertEqual(self.a.marks, snapshot[0])

    def test_clear_resets_marks_and_sequence_but_keeps_screen_and_supports_undo(self):
        snapshot = self.seed_screen_history()
        pinned = self.a.screen
        self.a.clear()
        self.assertIs(self.a.screen, pinned)
        self.assertEqual(self.a.marks, [])
        self.assertEqual(self.a.sequence.value(), 1)
        self.a.undo()
        self.assertEqual(self.a.marks, snapshot[0])
        self.assertEqual(self.a.sequence.value(), 9)

    def test_full_monitor_capture_uses_pinned_annotation_monitor(self):
        self.seed_screen_history()
        pinned = self.a.screen
        self.c.selected_screen = self.other_screen()
        self.c.focus = QRectF(-900, 0, 200, 200)
        self.c.mode = "present"
        self.a.sync_capture_scope()
        self.a.capture_scope.button(1).click()
        with patch("annotations.QTimer.singleShot") as timer, patch.object(self.a, "finish_capture") as finish:
            self.a.capture()
            timer.call_args.args[1]()
            self.assertIs(finish.call_args.args[0], pinned)
            self.assertEqual(finish.call_args.args[1], QRectF(pinned.geometry()))
            self.assertFalse(self.a.move_screen_button.isEnabled())


    def test_capture_card_has_exactly_two_ready_image_actions(self):
        self.assertTrue(self.a.captured.isNull())
        box = self.a.capture_button.parentWidget()
        buttons = box.findChildren(QPushButton, options=Qt.FindChildOption.FindDirectChildrenOnly)
        self.assertEqual([button.text() for button in buttons], ["Capture Image", "Save Image"])
        for button in buttons:
            self.assertTrue(button.isEnabled())
            self.assertEqual(button.accessibleName(), button.text())
            self.assertIn("fresh screenshot", button.toolTip())

    def test_save_image_captures_fresh_pixels_each_time_and_preserves_clipboard(self):
        screen = self.app.primaryScreen()
        clipboard = QPixmap(20, 20)
        clipboard.fill(QColor("#774411"))
        self.app.clipboard().setPixmap(clipboard)
        self.a.captured = clipboard
        with tempfile.TemporaryDirectory(prefix="spotlight-save-") as folder:
            path = Path(folder) / "chosen image"

            def choose_location(*args):
                self.assertIs(args[0], self.c.panel)
                self.assertTrue(self.c.panel.isVisible())
                self.assertTrue(self.a.capturing)
                self.assertFalse(self.a.capture_button.isEnabled())
                self.assertFalse(self.a.save_button.isEnabled())
                return str(path), "PNG image (*.png)"

            for color in ("#11aa33", "#3355cc"):
                fresh = QPixmap(screen.geometry().size())
                fresh.fill(QColor(color))
                with patch("annotations.QTimer.singleShot") as timer, patch.object(type(screen), "grabWindow", return_value=fresh) as grab, patch("annotations.QFileDialog.getSaveFileName", side_effect=choose_location) as dialog:
                    self.a.save_button.click()
                    self.assertTrue(self.a.capturing)
                    self.assertFalse(self.c.panel.isVisible())
                    dialog.assert_not_called()
                    self.a.capture()
                    self.a.save()
                    self.assertEqual(timer.call_count, 1)
                    timer.call_args.args[1]()
                    grab.assert_called_once_with(0)
                    dialog.assert_called_once()
                image = QImage(str(path) + ".png")
                self.assertFalse(image.isNull())
                self.assertEqual(image.pixelColor(10, 10), QColor(color))
                self.assertEqual(self.a.status.text(), "Image saved")
                self.assertFalse(self.a.capturing)
                self.assertTrue(self.a.capture_button.isEnabled())
                self.assertTrue(self.a.save_button.isEnabled())
                self.assertEqual(self.app.clipboard().pixmap().toImage(), clipboard.toImage())

    def test_cancel_save_restores_controls_and_keeps_clipboard(self):
        screen = self.app.primaryScreen()
        clipboard = QPixmap(20, 20)
        clipboard.fill(QColor("red"))
        self.app.clipboard().setPixmap(clipboard)
        fresh = QPixmap(screen.geometry().size())
        fresh.fill(QColor("green"))
        with patch("annotations.QTimer.singleShot") as timer, patch.object(type(screen), "grabWindow", return_value=fresh), patch("annotations.QFileDialog.getSaveFileName", return_value=("", "")) as dialog:
            self.a.save_button.click()
            timer.call_args.args[1]()
            dialog.assert_called_once()
        self.assertEqual(self.a.status.text(), "Save canceled")
        self.assertFalse(self.a.capturing)
        self.assertTrue(self.c.panel.isVisible())
        self.assertTrue(self.a.capture_button.isEnabled())
        self.assertTrue(self.a.save_button.isEnabled())
        self.assertEqual(self.app.clipboard().pixmap().toImage(), clipboard.toImage())

    def test_failed_save_capture_does_not_offer_stale_image(self):
        previous = QPixmap(20, 20)
        previous.fill(QColor("red"))
        self.a.captured = previous
        screen = self.app.primaryScreen()
        with patch("annotations.QTimer.singleShot") as timer, patch.object(type(screen), "grabWindow", return_value=QPixmap()), patch("annotations.QFileDialog.getSaveFileName") as dialog:
            self.a.save_button.click()
            timer.call_args.args[1]()
            dialog.assert_not_called()
        self.assertEqual(self.a.captured.toImage(), previous.toImage())
        self.assertIn("unavailable", self.a.status.text())
        self.assertFalse(self.a.capturing)
        self.assertTrue(self.c.panel.isVisible())
        self.assertTrue(self.a.capture_button.isEnabled())
        self.assertTrue(self.a.save_button.isEnabled())

    def test_failed_file_write_restores_both_capture_actions(self):
        screen = self.app.primaryScreen()
        fresh = QPixmap(screen.geometry().size())
        fresh.fill(QColor("green"))
        with patch("annotations.QTimer.singleShot") as timer, patch.object(type(screen), "grabWindow", return_value=fresh), patch("annotations.QFileDialog.getSaveFileName", return_value=("chosen.png", "PNG image (*.png)")), patch.object(QPixmap, "save", return_value=False):
            self.a.save_button.click()
            timer.call_args.args[1]()
        self.assertEqual(self.a.status.text(), "Could not save image")
        self.assertFalse(self.a.capturing)
        self.assertTrue(self.a.capture_button.isEnabled())
        self.assertTrue(self.a.save_button.isEnabled())
        self.assertTrue(self.c.panel.isVisible())
