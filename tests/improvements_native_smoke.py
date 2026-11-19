"""Native Windows check and panel-only previews for the controls redesign."""
import os
os.environ['QT_QPA_PLATFORM'] = 'windows'
import ctypes
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
from annotations import Mark
from spotlight import Spotlight

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
c = Spotlight(app, persist=False)
a = c.annotations
out = Path(__file__).resolve().parents[1] / 'previews'
out.mkdir(exist_ok=True)
try:
    c.show_panel()
    QTest.qWait(200)
    assert 6 in c.hotkeys.registered, 'Ctrl+Shift+D did not register: ' + str(c.hotkey_errors)
    # Exercise actual QScreens, including negative origins and mixed display scales.
    screens = app.screens()
    a.start()
    a.marks = [Mark('pen', '#ff0000', 4, 40, [QPointF(100, 100)])]
    for screen in screens:
        def confirm_move():
            dialog = app.activeModalWidget()
            assert isinstance(dialog, QMessageBox)
            dialog.button(QMessageBox.StandardButton.Yes).click()
        if screen is not a.screen:
            QTimer.singleShot(80, confirm_move)
            a.change_screen(screen)
        QTest.qWait(120)
        assert a.screen is screen
        assert a.overlay.geometry() == screen.geometry(), (a.overlay.geometry(), screen.geometry())
        assert a.overlay.windowHandle().screen() is screen, ('Native surface on wrong screen', screen.name())
        a.interact()
        a.start()
        assert a.screen is screen and len(a.marks) == 1
        shot = screen.grabWindow(0)
        assert not shot.isNull()
        assert abs(shot.width() - screen.geometry().width() * shot.devicePixelRatio()) <= 1
    a.marks = []
    a.history = []
    a.change_screen(app.primaryScreen(), confirm=False)
    for tab, name in ((0, 'spotlight'), (1, 'annotation')):
        c.panel.tabs.setCurrentIndex(tab)
        QTest.qWait(240)
        for control in (a.capture_button, a.save_button, a.draw_button, a.desktop_button):
            pos = control.mapTo(c.panel, QPoint())
            assert c.panel.rect().contains(pos) and c.panel.rect().contains(pos + control.rect().bottomRight())
        assert c.panel.grab().save(str(out / (name + '.png')))
    original = a.screen
    a.set_tool('text')
    def enter_text():
        dialog = app.activeModalWidget()
        assert isinstance(dialog, QInputDialog)
        dialog.setTextValue('Review this section\nText annotations are ready')
        dialog.accept()
    QTimer.singleShot(100, enter_text)
    a.add_text(QPointF(100, 100))
    assert len(a.marks) == 1 and a.marks[0].tool == 'text'
    assert a.drawing
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    assert user32.PostThreadMessageW(kernel32.GetCurrentThreadId(), 0x0312, 6, 0)
    QTest.qWait(100)
    assert not a.drawing
    assert user32.PostThreadMessageW(kernel32.GetCurrentThreadId(), 0x0312, 6, 0)
    QTest.qWait(100)
    assert a.drawing and a.tool == 'text' and a.screen is original and len(a.marks) == 1
    image = QImage(640, 240, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor('white'))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    Mark('horizontal_highlighter', '#ffdc32', 30, 40, [QPointF(36, 70), QPointF(430, 70)]).paint(painter)
    Mark('text', '#212121', 560, 28, [QPointF(36, 45)], 'Review this section\nText annotations are ready').paint(painter)
    Mark('arrow', '#e53935', 4, 40, [QPointF(530, 170), QPointF(450, 95)]).paint(painter)
    painter.end()
    assert image.save(str(out / 'annotation-example.png'))
    for width, height in ((360, 480), (700, 850)):
        c.panel.resize(width, height)
        QTest.qWait(100)
        for control in (a.capture_button, a.save_button, a.draw_button, a.desktop_button):
            pos = control.mapTo(c.panel, QPoint())
            assert c.panel.rect().contains(pos) and c.panel.rect().contains(pos + control.rect().bottomRight())
    print('PASS: native text dialog commits; Ctrl+Shift+D registered and native messages toggle without state loss; fixed actions visible on both tabs and resized panels; previews rendered')
    print('Physical screens:', [(s.name(), s.geometry().getRect(), s.devicePixelRatio()) for s in app.screens()])
finally:
    c.shutdown()
    c.panel.hide()
