"""Spatial monitor picker behavior independent of physical display hardware."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import unittest
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from annotations import MonitorSelector


class MonitorMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.selector = MonitorSelector()
        self.entries = [('left', '3: LG QHD (1440 x 2560)', QRect(-1440, -376, 1440, 2560)),
                        ('center', '1: PHL 438P1 (3072 x 1728)', QRect(0, 0, 3072, 1728)),
                        ('right', '2: LS32CG51x (1440 x 2560)', QRect(3840, -386, 1440, 2560))]
        for key, label, rect in self.entries:
            self.selector.addItem(label, key)
        self.selector.setCurrentIndex(1)
        self.selector.set_monitors(self.entries)
        self.selector.show()

    def tearDown(self):
        self.selector.hidePopup()
        self.selector.close()
        self.selector.deleteLater()
        self.app.processEvents()

    def test_spatial_layout_names_and_selection(self):
        self.selector.showPopup()
        popup = self.selector.monitor_popup
        self.app.processEvents()
        left, center, right = popup.tiles
        self.assertLess(left.geometry().right(), center.geometry().left())
        self.assertLess(center.geometry().right(), right.geometry().left())
        self.assertGreater(left.height(), left.width())
        self.assertGreater(center.width(), center.height())
        self.assertTrue(center.isChecked())
        self.assertEqual([row.text() for row in popup.rows], [e[1] for e in self.entries])
        self.assertTrue(all(popup.canvas.rect().contains(tile.geometry()) for tile in popup.tiles))

    def test_click_selects_key_and_closes(self):
        self.selector.showPopup()
        popup = self.selector.monitor_popup
        popup.tiles[2].click()
        self.assertEqual(self.selector.currentData(), 'right')
        self.assertFalse(popup.isVisible())

    def test_keyboard_escape_preserves_and_enter_selects(self):
        self.selector.showPopup()
        popup = self.selector.monitor_popup
        QTest.keyClick(popup.rows[1], Qt.Key.Key_Escape)
        self.assertFalse(popup.isVisible())
        self.assertEqual(self.selector.currentData(), 'center')
        self.selector.showPopup()
        popup = self.selector.monitor_popup
        QTest.keyClick(popup.rows[1], Qt.Key.Key_Down)
        QTest.keyClick(popup.rows[2], Qt.Key.Key_Return)
        self.assertEqual(self.selector.currentData(), 'right')

    def test_refresh_removes_disconnected_screen(self):
        self.selector.showPopup()
        self.selector.set_monitors(self.entries[:2])
        self.assertEqual(len(self.selector.monitor_popup.tiles), 2)
        self.selector.set_monitors([])
        self.assertEqual(len(self.selector.monitor_popup.tiles), 0)


if __name__ == '__main__':
    unittest.main()
