"""Run with: py -m unittest discover -s tests -v (no desktop windows)."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
import tempfile
import json
from math import cos, sin, pi
from unittest.mock import patch
from unittest.mock import Mock
import subprocess
import sys

from emergency import EmergencyExit, SystemCursor

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSettings, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from spotlight import DIM_PRESETS, Overlay, Spotlight, circle_hit, rectangle_hit, move_rect, selection_rect


class GeometryTests(unittest.TestCase):
    def test_reverse_drag_on_negative_origin_monitor(self):
        bounds = QRectF(-1920, -200, 1920, 1080)
        rect = selection_rect(QPointF(-100, 300), QPointF(-500, 100), bounds, False)
        self.assertEqual(rect, QRectF(-500, 100, 400, 200))

    def test_circle_clips_to_screen_and_stays_square(self):
        rect = selection_rect(QPointF(50, 50), QPointF(900, 700), QRectF(0, 0, 400, 300), True)
        self.assertEqual(rect, QRectF(50, 50, 250, 250))

    def test_move_clamps_all_edges(self):
        bounds = QRectF(-800, 0, 800, 600)
        rect = QRectF(-600, 100, 200, 150)
        self.assertEqual(move_rect(rect, QPointF(-900, -900), bounds), QRectF(-800, 0, 200, 150))
        self.assertEqual(move_rect(rect, QPointF(900, 900), bounds), QRectF(-200, 450, 200, 150))


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.c = Spotlight(self.app, native_hotkeys=False, persist=False)
        self.o = self.c.overlays[0]
        self.tray_available = patch("spotlight.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
        self.tray_available.start()
        self.addCleanup(self.tray_available.stop)

    def tearDown(self):
        self.c.shutdown()
        self.c.panel.hide()
        for overlay in self.c.overlays:
            overlay.deleteLater()
        self.c.panel.deleteLater()
        self.app.processEvents()

    def seed(self):
        self.c.selected_screen = self.o.screen_ref
        origin = QPointF(self.o.screen_ref.geometry().topLeft())
        self.c.focus = QRectF(100, 120, 200, 160).translated(origin)

    def test_drag_selection_remains_editable_and_escape_clears(self):
        self.c.select()
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(100, 120))
        QTest.mouseMove(self.o, QPoint(300, 280))
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(300, 280))
        self.assertEqual(self.c.mode, "edit")
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(180, 200))
        QTest.mouseMove(self.o, QPoint(220, 230))
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(220, 230))
        self.assertEqual(self.o.local_rect(), QRectF(140, 150, 200, 160))
        self.c.lock()
        self.assertEqual(self.c.focus.size().width(), 200)
        self.assertTrue(self.o.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.c.edit()
        self.assertFalse(self.o.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        QTest.keyClick(self.o, Qt.Key.Key_Escape)
        self.assertEqual(self.c.mode, "off")
        self.assertFalse(self.o.isVisible())
        self.assertTrue(self.c.panel.isVisible())
        self.assertFalse(self.c.panel.isMinimized())

    def test_circle_invisible_edge_resizes_after_selection(self):
        self.c.shape = "Circle"
        self.c.select()
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
        self.assertEqual(self.c.mode, "edit")
        image = self.render_overlay()
        self.assertEqual(image.pixelColor(300, 200).red(), 0)
        self.assertEqual(image.pixelColor(100, 100).red(), 0)
        for start, end, radius in (
            (QPoint(300, 200), QPoint(320, 200), 120),
            (QPoint(200, 80), QPoint(200, 100), 100),
            (QPoint(100, 200), QPoint(80, 200), 120),
            (QPoint(200, 320), QPoint(200, 300), 100),
        ):
            QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=end)
            self.assertEqual(self.o.local_rect(), QRectF(200-radius, 200-radius, 2*radius, 2*radius))
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(200, 200))
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(220, 230))
        self.assertEqual(self.o.local_rect(), QRectF(120, 130, 200, 200))

    def test_circle_resize_anywhere_on_edge_without_jump(self):
        self.c.shape = "Circle"
        self.seed()
        self.c.edit()
        for index in range(50):
            self.c.focus = QRectF(100, 100, 200, 200).translated(QPointF(self.o.geometry().topLeft()))
            angle = 2 * pi * index / 50
            start = QPoint(round(200 + 106 * cos(angle)), round(200 + 106 * sin(angle)))
            end = QPoint(round(200 + 126 * cos(angle)), round(200 + 126 * sin(angle)))
            global_start = QPointF(self.o.mapToGlobal(start))
            kind, cursor = circle_hit(self.c.focus, global_start)
            self.assertEqual(kind, "resize")
            self.assertIn(cursor, (Qt.CursorShape.SizeHorCursor, Qt.CursorShape.SizeVerCursor,
                                  Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeBDiagCursor))
            QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=start)
            self.assertAlmostEqual(self.c.focus.width(), 200)
            QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=end)
            self.assertAlmostEqual(self.c.focus.width(), 240, delta=3)
            self.assertEqual(self.o.local_rect().center(), QPointF(200, 200))
        rect = QRectF(100, 100, 200, 200)
        self.assertEqual(circle_hit(rect, QPointF(200, 200)), ("move", Qt.CursorShape.SizeAllCursor))
        self.assertEqual(circle_hit(rect, QPointF(100, 100)), (None, Qt.CursorShape.ArrowCursor))

    def test_rectangle_invisible_edges_and_corners_resize(self):
        self.seed()
        self.c.edit()
        original = QRectF(self.c.focus)
        image = self.render_overlay()
        for point in (QPoint(100, 120), QPoint(300, 120), QPoint(100, 280), QPoint(300, 280), QPoint(200, 120)):
            self.assertEqual(image.pixelColor(point).red(), 0)
            self.assertEqual(image.pixelColor(point).blue(), 0)
        for start, end, expected in (
            (QPoint(94, 200), QPoint(74, 200), QRectF(80, 120, 220, 160)),
            (QPoint(306, 200), QPoint(326, 200), QRectF(100, 120, 220, 160)),
            (QPoint(200, 114), QPoint(200, 94), QRectF(100, 100, 200, 180)),
            (QPoint(200, 286), QPoint(200, 306), QRectF(100, 120, 200, 180)),
            (QPoint(94, 114), QPoint(74, 94), QRectF(80, 100, 220, 180)),
            (QPoint(306, 114), QPoint(326, 94), QRectF(100, 100, 220, 180)),
            (QPoint(94, 286), QPoint(74, 306), QRectF(80, 120, 220, 180)),
            (QPoint(306, 286), QPoint(326, 306), QRectF(100, 120, 220, 180)),
        ):
            self.c.focus = QRectF(original)
            QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=start)
            self.assertEqual(self.c.focus, original)
            QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=end)
            self.assertEqual(self.o.local_rect(), expected)
        rect = QRectF(100, 120, 200, 160)
        for x in range(120, 281, 8):
            self.assertEqual(rectangle_hit(rect, QPointF(x, 120)), ("t", Qt.CursorShape.SizeVerCursor))
        for y in range(140, 261, 8):
            self.assertEqual(rectangle_hit(rect, QPointF(300, y)), ("r", Qt.CursorShape.SizeHorCursor))
        self.assertEqual(rectangle_hit(rect, QPointF(100, 120)), ("tl", Qt.CursorShape.SizeFDiagCursor))
        self.assertEqual(rectangle_hit(rect, QPointF(300, 120)), ("tr", Qt.CursorShape.SizeBDiagCursor))
        self.assertEqual(rectangle_hit(rect, QPointF(200, 200)), ("move", Qt.CursorShape.SizeAllCursor))
        self.assertEqual(rectangle_hit(rect, QPointF(50, 50)), (None, Qt.CursorShape.ArrowCursor))

    def test_dimming_presets_and_keyboard(self):
        self.seed()
        self.c.edit()
        self.assertEqual(tuple(self.c.panel.dim_buttons), DIM_PRESETS)
        for value, button in self.c.panel.dim_buttons.items():
            button.click()
            self.assertEqual(self.c.dim, value)
            self.assertEqual(self.c.panel.dim_slider.value(), value)
            self.assertEqual(sum(b.isChecked() for b in self.c.panel.dim_buttons.values()), 1)
        QTest.keyClick(self.o, Qt.Key.Key_Minus)
        self.assertEqual(self.c.dim, 95)
        QTest.keyClick(self.o, Qt.Key.Key_Plus)
        self.assertEqual(self.c.dim, 100)
        QTest.keyClick(self.o, Qt.Key.Key_Plus)
        self.assertEqual(self.c.dim, 100)

    def test_slider_intermediate_value_renders_and_keyboard_steps_to_presets(self):
        self.seed()
        self.c.edit()
        self.c.panel.dim_slider.setValue(43)
        self.assertEqual(self.c.dim, 43)
        self.assertEqual(self.c.panel.dim_label.text(), '43')
        self.assertFalse(any(b.isChecked() for b in self.c.panel.dim_buttons.values()))
        self.assertAlmostEqual(self.render_overlay().pixelColor(20, 100).alpha(), 110, delta=1)
        QTest.keyClick(self.o, Qt.Key.Key_Plus)
        self.assertEqual(self.c.dim, 50)
        self.assertEqual(self.c.panel.dim_slider.value(), 50)
        self.c.panel.dim_slider.setValue(43)
        QTest.keyClick(self.o, Qt.Key.Key_Minus)
        self.assertEqual(self.c.dim, 30)
        self.assertTrue(self.c.panel.dim_buttons[30].isChecked())

    def test_restart_keeps_settings_without_restoring_area(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(directory + '/prefs.ini', QSettings.Format.IniFormat)
            self.c.settings = settings
            self.seed()
            self.c.edit()
            self.c.set_shape('Circle')
            self.c.set_dim(85)
            self.c.lock()
            self.c.shutdown()
            self.assertFalse(settings.contains('selection'))
            with patch('spotlight.QSettings', return_value=settings):
                restored = Spotlight(self.app, native_hotkeys=False)
            try:
                restored.show_panel()
                self.assertEqual(restored.shape, 'Circle')
                self.assertEqual(restored.dim, 85)
                self.assertTrue(restored.panel.dim_buttons[85].isChecked())
                self.assertEqual(restored.mode, 'off')
                self.assertTrue(restored.focus.isEmpty())
                self.assertIsNone(restored.selected_screen)
                self.assertTrue(all(not o.isVisible() for o in restored.overlays))
                self.assertTrue(restored.panel.status.text().startswith('Ready'))
                self.assertTrue(restored.panel.isVisible())
                self.assertFalse(restored.panel.isMinimized())
            finally:
                restored.shutdown()
                for overlay in restored.overlays:
                    overlay.deleteLater()
                restored.panel.deleteLater()
                self.app.processEvents()
                self.c.settings = None

    def test_legacy_saved_selection_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(directory + '/prefs.ini', QSettings.Format.IniFormat)
            for saved in ('bad json', json.dumps({'screen': self.o.screen_ref.name(), 'rect': [100, 100, 200, 200]})):
                settings.setValue('selection', saved)
                settings.setValue('dim', 100)
                with patch('spotlight.QSettings', return_value=settings):
                    restored = Spotlight(self.app, native_hotkeys=False)
                try:
                    self.assertEqual(restored.mode, 'off')
                    self.assertEqual(restored.dim, 100)
                    self.assertTrue(restored.focus.isEmpty())
                    self.assertTrue(all(not o.isVisible() for o in restored.overlays))
                    self.assertTrue(restored.panel.status.text().startswith('Ready'))
                finally:
                    restored.shutdown()
                    for overlay in restored.overlays:
                        overlay.deleteLater()
                    restored.panel.deleteLater()
                    self.app.processEvents()

    def test_only_selected_monitor_has_overlay(self):
        screen = Mock()
        screen.geometry.return_value = QRect(1000, 0, 800, 600)
        other = Overlay(self.c, screen)
        self.c.overlays.append(other)
        self.c.select()
        self.assertTrue(other.isVisible())
        self.seed()
        self.c.repaint()
        self.assertFalse(other.isVisible())
        for mode in ('edit', 'present'):
            self.c.activate(mode)
            self.assertTrue(self.o.isVisible())
            self.assertFalse(other.isVisible())
            image = QImage(other.size(), QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            other.render(image)
            self.assertEqual(image.pixelColor(50, 50).alpha(), 0)

    def test_new_area_replaces_existing_without_panel(self):
        self.seed()
        self.c.lock()
        self.c.select()
        self.assertEqual(self.c.mode, "select")
        self.assertTrue(self.c.focus.isEmpty())
        self.assertTrue(self.c.panel.isMinimized())
        QTest.mouseClick(self.o, Qt.MouseButton.RightButton, pos=QPoint(200, 200))
        self.assertEqual(self.c.mode, "off")
        self.assertTrue(self.c.panel.isVisible())
        self.assertFalse(self.c.panel.isMinimized())

    def test_controls_minimize_and_remain_available_during_spotlight(self):
        self.c.show_panel()
        self.c.select()
        self.assertTrue(self.c.panel.isVisible())
        self.assertTrue(self.c.panel.isMinimized())
        self.seed()
        self.c.lock()
        self.c.show_panel()
        self.assertTrue(self.c.panel.isVisible())
        self.assertFalse(self.c.panel.isMinimized())
        self.assertEqual(self.c.mode, "present")

    def test_keyboard_move_and_edit_toggle(self):
        self.seed()
        self.c.lock()
        original = QRectF(self.c.focus)
        self.c.toggle_edit()
        self.assertEqual(self.c.mode, "edit")
        QTest.keyClick(self.o, Qt.Key.Key_Right)
        QTest.keyClick(self.o, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.c.focus, original.translated(1, 10))
        self.c.toggle_edit()
        self.assertEqual(self.c.mode, "present")
        self.assertFalse(self.c.panel.isMinimized())

    def test_right_click_clears_edit_and_resets_drag(self):
        self.seed()
        self.c.edit()
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(180, 200))
        QTest.mouseClick(self.o, Qt.MouseButton.RightButton, pos=QPoint(180, 200))
        self.assertEqual(self.c.mode, "off")
        self.assertIsNone(self.o.drag_start)
        self.assertTrue(self.c.panel.isVisible())
        self.assertFalse(self.c.panel.isMinimized())

    def test_tiny_selection_does_not_lock(self):
        self.c.select()
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(100, 120))
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(100, 120))
        self.assertEqual(self.c.mode, "select")
        self.assertTrue(self.c.focus.isEmpty())

    def test_edit_move_resize_and_circle_shortcut(self):
        self.seed()
        self.c.edit()
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(180, 200))
        QTest.mouseMove(self.o, QPoint(220, 230))
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(220, 230))
        self.assertEqual(self.o.local_rect(), QRectF(140, 150, 200, 160))
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(340, 310))
        QTest.mouseMove(self.o, QPoint(380, 350))
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(380, 350))
        self.assertEqual(self.o.local_rect(), QRectF(140, 150, 240, 200))
        QTest.keyClick(self.o, Qt.Key.Key_C)
        self.assertEqual(self.c.shape, "Circle")
        self.assertEqual(self.c.focus.width(), self.c.focus.height())
        QTest.keyClick(self.o, Qt.Key.Key_Plus)
        self.assertEqual(self.c.dim, 75)
        QTest.keyClick(self.o, Qt.Key.Key_Return)
        self.assertEqual(self.c.mode, "present")

    def render_overlay(self):
        image = QImage(self.o.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        # Test spotlight paint independently of the controls' input exclusion.
        self.o.render(image, renderFlags=QWidget.RenderFlag.IgnoreMask)
        return image

    def test_presentation_has_clear_hole_and_dim_surroundings(self):
        self.seed()
        self.c.lock()
        image = self.render_overlay()
        self.assertEqual(image.pixelColor(180, 200).alpha(), 0)
        self.assertAlmostEqual(image.pixelColor(20, 100).alpha(), 128, delta=1)
        self.c.set_shape("Circle")
        image = self.render_overlay()
        self.assertEqual(image.pixelColor(200, 200).alpha(), 0)
        self.assertGreater(image.pixelColor(121, 121).alpha(), 120)

    def test_unchanged_geometry_notification_preserves_selection(self):
        self.seed()
        self.c.lock()
        expected = QRectF(self.c.focus)
        self.c.geometry_changed()
        self.assertEqual(self.c.mode, "present")
        self.assertEqual(self.c.focus, expected)
        self.assertTrue(self.o.isVisible())

    def test_geometry_notification_during_drag_does_not_interrupt_move(self):
        self.seed()
        self.c.edit()
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(180, 200))
        self.c.geometry_changed()
        self.assertEqual(self.o.drag_kind, "move")
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(210, 220))
        self.assertEqual(self.o.local_rect(), QRectF(130, 140, 200, 160))
        self.assertEqual(self.c.mode, "edit")

    def test_changed_screen_bounds_fit_selection_instead_of_clearing(self):
        self.seed()
        self.c.focus = QRectF(650, 650, 100, 100)
        self.c.lock()
        with patch.object(type(self.o.screen_ref), "geometry", return_value=QRect(50, 30, 400, 300)):
            self.c.geometry_changed()
        self.assertEqual(self.c.focus, QRectF(350, 230, 100, 100))
        self.assertEqual(self.c.mode, "present")

    def test_removed_selected_screen_clears_safely(self):
        self.seed()
        self.c.lock()
        with patch.object(self.app, "screens", return_value=[]):
            self.c.geometry_changed()
        self.assertTrue(self.c.focus.isEmpty())
        self.assertEqual(self.c.mode, "off")

    def test_screen_list_refresh_keeps_selected_area(self):
        self.seed()
        self.c.lock()
        expected = QRectF(self.c.focus)
        self.c.screens_changed()
        self.assertEqual(self.c.focus, expected)
        self.assertEqual(self.c.mode, "present")
        self.assertTrue(next(o for o in self.c.overlays if o.screen_ref == self.c.selected_screen).isVisible())

    def test_screen_refresh_during_drag_reuses_input_window(self):
        self.seed()
        self.c.edit()
        QTest.mousePress(self.o, Qt.MouseButton.LeftButton, pos=QPoint(180, 200))
        self.c.screens_changed()
        self.assertIs(self.c.overlays[0], self.o)
        self.assertEqual(self.o.drag_kind, "move")
        QTest.mouseRelease(self.o, Qt.MouseButton.LeftButton, pos=QPoint(210, 220))
        self.assertEqual(self.o.local_rect(), QRectF(130, 140, 200, 160))

    def test_screen_refresh_keeps_annotation_mode_and_marks(self):
        from annotations import Mark
        self.seed()
        self.c.panel.tabs.setCurrentIndex(1)
        mark = Mark("pen", "#e53935", 4, 40, [QPointF(100, 100), QPointF(150, 100)])
        self.c.annotations.marks = [mark]
        self.c.screens_changed()
        self.assertTrue(self.c.annotations.drawing)
        self.assertEqual(self.c.annotations.marks, [mark])
        self.assertFalse(self.c.focus.isEmpty())

    def test_editing_uses_full_dimming_and_updates_live(self):
        self.seed()
        self.c.panel.dim_buttons[100].click()
        self.c.lock()
        image = self.render_overlay()
        self.assertEqual(image.pixelColor(20, 100).alpha(), 255)
        self.assertEqual(image.pixelColor(180, 200).alpha(), 0)
        self.c.edit()
        self.assertEqual(self.render_overlay().pixelColor(20, 100).alpha(), 255)
        self.assertEqual(self.c.dim, 100)
        self.c.panel.dim_buttons[85].click()
        self.assertAlmostEqual(self.render_overlay().pixelColor(20, 100).alpha(), 217, delta=1)
        self.assertEqual(self.c.mode, "edit")

    def test_overlay_has_no_persistent_banners(self):
        self.seed()
        self.c.edit()
        image = self.render_overlay()
        self.assertAlmostEqual(image.pixelColor(40, 40).alpha(), 128, delta=1)
        self.assertEqual(image.pixelColor(40, 40).red(), 0)
        self.assertFalse(self.c.panel.isMinimized())

    def test_escape_poll_does_not_require_native_hotkey_event(self):
        self.seed()
        self.c.lock()
        self.c.emergency = EmergencyExit(key_down=lambda: True, terminate=Mock())
        self.c.poll_escape()
        self.assertEqual(self.c.mode, "off")

    def test_timeout_only_clears_unfinished_selection(self):
        self.c.select()
        self.assertTrue(self.c.interaction_timer.isActive())
        self.c.expire_interaction()
        self.assertEqual(self.c.mode, "off")
        self.seed()
        self.c.edit()
        self.assertFalse(self.c.interaction_timer.isActive())
        self.c.expire_interaction()
        self.assertEqual(self.c.mode, "edit")
        self.seed()
        self.c.lock()
        self.assertFalse(self.c.interaction_timer.isActive())
        self.c.expire_interaction()
        self.assertEqual(self.c.mode, "present")


class CursorTests(unittest.TestCase):
    def test_hide_and_restore_balance_and_preserve_cursor_theme(self):
        api = Mock()
        cursor = SystemCursor(api=api)
        cursor.set_hidden(True)
        cursor.set_hidden(True)
        self.assertTrue(cursor.hidden)
        api.MagInitialize.assert_called_once()
        api.MagShowSystemCursor.assert_called_once_with(False)
        cursor.restore()
        cursor.restore()
        self.assertFalse(cursor.hidden)
        self.assertEqual(api.MagShowSystemCursor.call_args_list, [((False,),), ((True,),)])
        cursor.close()
        api.MagUninitialize.assert_called_once()

    def test_failed_hide_or_restore_can_retry(self):
        api = Mock()
        api.MagInitialize.return_value = 1
        api.MagShowSystemCursor.side_effect = [0, 1, 0, 1]
        cursor = SystemCursor(api=api)
        cursor.set_hidden(True)
        self.assertFalse(cursor.hidden)
        cursor.set_hidden(True)
        self.assertTrue(cursor.hidden)
        cursor.restore()
        self.assertTrue(cursor.hidden)
        cursor.close()
        self.assertFalse(cursor.hidden)
        api.MagUninitialize.assert_called_once()

    def test_emergency_exit_restores_pointer_before_terminating(self):
        actions = []
        guard = EmergencyExit(key_down=lambda: True, cleanup=lambda: actions.append("show cursor"),
                              terminate=lambda: actions.append("exit"))
        guard.active.set()
        guard.check(0)
        guard.check(2.1)
        self.assertEqual(actions, ["show cursor", "exit"])


class EmergencyTests(unittest.TestCase):
    def test_only_continuous_hold_while_active_exits(self):
        key = Mock(return_value=True)
        terminate = Mock()
        guard = EmergencyExit(key_down=key, terminate=terminate)
        guard.check(0)
        guard.check(5)
        terminate.assert_not_called()
        guard.active.set()
        guard.check(6)
        guard.check(7)
        terminate.assert_not_called()
        key.return_value = False
        guard.check(8)
        key.return_value = True
        guard.check(9)
        guard.check(11.1)
        terminate.assert_called_once()

    def test_worker_can_exit_without_ui_event_loop(self):
        code = ("from emergency import EmergencyExit, SystemCursor; import time; "
                "guard = EmergencyExit(key_down=lambda: True); "
                "guard.active.set(); guard.start(); time.sleep(8)")
        result = subprocess.run([sys.executable, "-c", code], timeout=6, capture_output=True)
        self.assertEqual(result.returncode, 2, result.stderr.decode())


if __name__ == "__main__":
    unittest.main()
