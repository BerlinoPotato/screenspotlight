import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

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
        self.assertTrue(self.a.copy_button.isEnabled())

    def test_capture_defaults_to_selection_with_monitor_fallback(self):
        self.c.selected_screen = self.app.primaryScreen()
        self.c.focus = QRectF(100, 100, 200, 150)
        with patch("annotations.QTimer.singleShot") as timer, patch.object(self.a, "finish_capture") as finish:
            self.a.capture()
            self.assertFalse(self.c.panel.isVisible())
            timer.call_args.args[1]()
            self.assertEqual(finish.call_args.args[1], QRectF(100, 100, 200, 150))
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
