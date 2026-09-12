"""Standalone Windows spotlight; launch directly or as a PLAR QProcess."""
from __future__ import annotations

import ctypes
from math import atan2, hypot, pi
from ctypes import wintypes
import sys
import tempfile
from pathlib import Path

from emergency import EmergencyExit

from PySide6.QtCore import (
    QAbstractNativeEventFilter, QLockFile, QPointF, QRectF, QSettings, Qt, QTimer,
)
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QHBoxLayout, QLabel, QMenu, QPushButton, QRadioButton,
    QDialog, QMessageBox, QSystemTrayIcon, QVBoxLayout, QWidget,
)


DIM_PRESETS = (10, 20, 30, 50, 75, 85, 95, 100)
APP_VERSION = "0.1.18"
WINDOW_TITLE = "Screen Spotlight"
MIN_SIZE = 24.0


def selection_rect(start: QPointF, end: QPointF, bounds: QRectF, circle: bool) -> QRectF:
    """Constrain a drag to one screen; circles always have equal dimensions."""
    end = QPointF(max(bounds.left(), min(end.x(), bounds.right())),
                  max(bounds.top(), min(end.y(), bounds.bottom())))
    dx, dy = end.x() - start.x(), end.y() - start.y()
    if circle:
        side = min(abs(dx), abs(dy))
        dx = side if dx >= 0 else -side
        dy = side if dy >= 0 else -side
    return QRectF(start, start + QPointF(dx, dy)).normalized()


def move_rect(rect: QRectF, delta: QPointF, bounds: QRectF) -> QRectF:
    result = QRectF(rect)
    result.moveLeft(max(bounds.left(), min(rect.left() + delta.x(), bounds.right() - rect.width())))
    result.moveTop(max(bounds.top(), min(rect.top() + delta.y(), bounds.bottom() - rect.height())))
    return result


def rectangle_hit(rect: QRectF, point: QPointF):
    """Hit-test every edge and corner using the same invisible grab margin."""
    margin = min(10, rect.width() / 3, rect.height() / 3)
    if rect.isEmpty() or not rect.adjusted(-margin, -margin, margin, margin).contains(point):
        return None, Qt.CursorShape.ArrowCursor
    horizontal = "l" if abs(point.x() - rect.left()) <= margin else "r" if abs(point.x() - rect.right()) <= margin else ""
    vertical = "t" if abs(point.y() - rect.top()) <= margin else "b" if abs(point.y() - rect.bottom()) <= margin else ""
    kind = vertical + horizontal
    if vertical and horizontal:
        cursor = Qt.CursorShape.SizeFDiagCursor if kind in ("tl", "br") else Qt.CursorShape.SizeBDiagCursor
    elif horizontal:
        cursor = Qt.CursorShape.SizeHorCursor
    elif vertical:
        cursor = Qt.CursorShape.SizeVerCursor
    else:
        return "move", Qt.CursorShape.SizeAllCursor
    return kind, cursor


def circle_hit(rect: QRectF, point: QPointF):
    """The full circumference is a resize target, with a forgiving invisible band."""
    delta = point - rect.center()
    distance = hypot(delta.x(), delta.y())
    radius = rect.width() / 2
    if radius > 0 and abs(distance - radius) <= min(10, radius / 3):
        direction = round(atan2(delta.y(), delta.x()) / (pi / 4)) % 4
        cursor = (Qt.CursorShape.SizeHorCursor, Qt.CursorShape.SizeFDiagCursor,
                  Qt.CursorShape.SizeVerCursor, Qt.CursorShape.SizeBDiagCursor)[direction]
        return "resize", cursor
    if distance < radius:
        return "move", Qt.CursorShape.SizeAllCursor
    return None, Qt.CursorShape.ArrowCursor


class Hotkeys(QAbstractNativeEventFilter):
    """Thread-level Windows hotkeys, received through Qt's native dispatcher."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.registered = {}
        self.user32 = ctypes.WinDLL("user32", use_last_error=True) if sys.platform == "win32" else None
        if self.user32:
            self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user32.RegisterHotKey.restype = wintypes.BOOL
            self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.UnregisterHotKey.restype = wintypes.BOOL

    def register(self, ident, modifiers, key, callback):
        if ident in self.registered:
            return True
        if self.user32 and self.user32.RegisterHotKey(None, ident, modifiers | 0x4000, key):
            self.registered[ident] = callback
            return True
        return False

    def unregister(self, ident):
        if ident in self.registered:
            self.user32.UnregisterHotKey(None, ident)
            del self.registered[ident]

    def close(self):
        for ident in list(self.registered):
            self.unregister(ident)

    def nativeEventFilter(self, event_type, message):
        if self.user32 and bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and int(msg.wParam) in self.registered:
                QTimer.singleShot(0, self.registered[int(msg.wParam)])
                return True, 0
        return False, 0


class Overlay(QWidget):
    def __init__(self, controller, screen):
        super().__init__()
        self.controller = controller
        self.screen_ref = screen
        self.drag_start = None
        self.original = QRectF()
        self.drag_kind = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setWindowTitle("Screen Spotlight overlay")

    def present(self):
        self.drag_start = self.drag_kind = None
        if self.controller.selected_screen is not None and self.screen_ref != self.controller.selected_screen:
            self.hide()
            return
        editing = self.controller.mode in ("select", "edit")
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        if not editing:
            flags |= Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not editing)
        self.setGeometry(self.screen_ref.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor if self.controller.mode == "select" else Qt.CursorShape.ArrowCursor)
        self.show()
        self.update()

    def local_rect(self):
        return self.controller.focus.translated(-QPointF(self.geometry().topLeft()))

    def paintEvent(self, event):
        c = self.controller
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        if c.selected_screen is not None and self.screen_ref != c.selected_screen:
            painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
            painter.end()
            return
        # Always clear previous frames, including the previous hole.
        # Keep the desktop visible while drawing a new area. Once selected,
        # editable and locked areas both use the user's full dimming value.
        opacity = min(c.dim, 75) if c.mode == "select" else c.dim
        painter.fillRect(self.rect(), QColor(0, 0, 0, round(opacity * 255 / 100)))
        r = self.local_rect()
        if not c.focus.isEmpty():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.GlobalColor.transparent)
            if c.shape == "Circle":
                painter.drawEllipse(r)
            else:
                painter.drawRect(r)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            if c.mode in ("edit", "select"):
                # Almost transparent fill keeps the hole interactive during editing.
                if c.shape == "Circle":
                    painter.setBrush(QColor(0, 0, 0, 8))
                    painter.drawEllipse(r)
                else:
                    painter.fillRect(r, QColor(0, 0, 0, 8))
        painter.end()

    def mousePressEvent(self, event):
        c = self.controller
        c.touch_interaction()
        if event.button() == Qt.MouseButton.RightButton and c.mode in ("select", "edit"):
            c.clear()
            return
        if event.button() != Qt.MouseButton.LeftButton or c.mode not in ("select", "edit"):
            return
        point = event.globalPosition()
        self.drag_start = point
        self.original = QRectF(c.focus)
        if c.mode == "select":
            c.selected_screen = self.screen_ref
            c.focus = QRectF(point, point)
            self.drag_kind = "select"
        elif c.selected_screen == self.screen_ref:
            hit_test = circle_hit if c.shape == "Circle" else rectangle_hit
            self.drag_kind, cursor = hit_test(c.focus, point)
            self.setCursor(cursor)
        else:
            self.drag_kind = None
        c.repaint()

    def mouseMoveEvent(self, event):
        c = self.controller
        if self.drag_start is not None:
            c.touch_interaction()
        point = event.globalPosition()
        if self.drag_start is None or self.drag_kind is None:
            if c.mode == "edit":
                hit_test = circle_hit if c.shape == "Circle" else rectangle_hit
                _, cursor = hit_test(c.focus, point)
                self.setCursor(cursor)
            return
        bounds = QRectF(self.screen_ref.geometry())
        if self.drag_kind == "select":
            c.focus = selection_rect(self.drag_start, point, bounds, c.shape == "Circle")
        elif self.drag_kind == "move":
            c.focus = move_rect(self.original, point - self.drag_start, bounds)
        elif c.shape == "Circle":
            center = self.original.center()
            delta = point - center
            start_delta = self.drag_start - center
            # Preserve the grab offset so pressing near the edge never jumps in size.
            radius = self.original.width() / 2 + hypot(delta.x(), delta.y()) - hypot(start_delta.x(), start_delta.y())
            radius = min(max(MIN_SIZE / 2, radius),
                         center.x() - bounds.left(), bounds.right() - center.x(),
                         center.y() - bounds.top(), bounds.bottom() - center.y())
            c.focus = QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
        else:
            candidate = QRectF(self.original)
            delta = point - self.drag_start
            if "l" in self.drag_kind:
                candidate.setLeft(max(bounds.left(), min(self.original.left() + delta.x(), self.original.right() - MIN_SIZE)))
            if "r" in self.drag_kind:
                candidate.setRight(min(bounds.right(), max(self.original.right() + delta.x(), self.original.left() + MIN_SIZE)))
            if "t" in self.drag_kind:
                candidate.setTop(max(bounds.top(), min(self.original.top() + delta.y(), self.original.bottom() - MIN_SIZE)))
            if "b" in self.drag_kind:
                candidate.setBottom(min(bounds.bottom(), max(self.original.bottom() + delta.y(), self.original.top() + MIN_SIZE)))
            c.focus = candidate
        c.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        # Finalize from the release position even if Windows coalesced the move events.
        if self.drag_start is not None and self.drag_kind is not None:
            self.mouseMoveEvent(event)
        was_select = self.drag_kind == "select"
        self.drag_start = self.drag_kind = None
        if was_select:
            if self.controller.focus.width() >= MIN_SIZE and self.controller.focus.height() >= MIN_SIZE:
                self.controller.edit()
            else:
                self.controller.focus = QRectF()
                self.controller.repaint()

    def keyPressEvent(self, event):
        c = self.controller
        c.touch_interaction()
        key = event.key()
        if key == Qt.Key.Key_Escape:
            c.clear()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            c.lock()
        elif key == Qt.Key.Key_R:
            c.set_shape("Rectangle")
        elif key == Qt.Key.Key_C:
            c.set_shape("Circle")
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            c.step_dim(1)
        elif key == Qt.Key.Key_Minus:
            c.step_dim(-1)
        elif c.mode == "edit" and key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx, dy = {Qt.Key.Key_Left: (-step, 0), Qt.Key.Key_Right: (step, 0),
                      Qt.Key.Key_Up: (0, -step), Qt.Key.Key_Down: (0, step)}[key]
            c.focus = move_rect(c.focus, QPointF(dx, dy), QRectF(c.selected_screen.geometry()))
            c.repaint()
        else:
            super().keyPressEvent(event)


class Panel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)
        title = QLabel("Screen Spotlight")
        title.setStyleSheet("font-size: 25px; font-weight: 650;")
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        self.info_button = QPushButton("ⓘ")
        self.info_button.setAccessibleName("Information and keyboard shortcuts")
        self.info_button.setToolTip("Information and keyboard shortcuts")
        self.info_button.setFixedSize(36, 36)
        self.info_button.clicked.connect(self.show_information)
        header.addWidget(self.info_button)
        layout.addLayout(header)
        layout.addWidget(QLabel("Highlight shape"))
        self.shape_group = QButtonGroup(self)
        self.shape_buttons = {}
        shape_row = QHBoxLayout()
        for name in ("Rectangle", "Circle"):
            button = QRadioButton(name)
            self.shape_group.addButton(button)
            self.shape_buttons[name] = button
            button.setChecked(name == controller.shape)
            shape_row.addWidget(button)
        self.shape_group.buttonClicked.connect(lambda button: controller.set_shape(button.text()))
        layout.addLayout(shape_row)
        self.dim_label = QLabel()
        layout.addWidget(self.dim_label)
        self.dim_group = QButtonGroup(self)
        self.dim_buttons = {}
        dim_row = QHBoxLayout()
        dim_row.setSpacing(12)
        for value in DIM_PRESETS:
            button = QRadioButton(f"{value}%")
            self.dim_group.addButton(button, value)
            self.dim_buttons[value] = button
            button.setChecked(value == controller.dim)
            dim_row.addWidget(button)
        self.dim_group.idClicked.connect(controller.set_dim)
        layout.addLayout(dim_row)
        self.dim_label.setText("Background dimming")
        select = QPushButton("Select area")
        select.setObjectName("primary")
        select.clicked.connect(controller.select)
        layout.addWidget(select)
        row = QHBoxLayout()
        for label, action in [("Move / resize", controller.edit), ("Lock / present", controller.lock), ("Clear", controller.clear)]:
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        self.status = QLabel("Ready — select an area to begin.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.information = QDialog(self)
        self.information.setWindowTitle("Information")
        self.information.setWindowModality(Qt.WindowModality.WindowModal)
        info_layout = QVBoxLayout(self.information)
        info_layout.setContentsMargins(24, 24, 24, 24)
        info_layout.setSpacing(16)
        info_title = QLabel("Screen Spotlight")
        info_title.setStyleSheet("font-size: 20px; font-weight: 650;")
        info_layout.addWidget(info_title)
        help_text = QLabel(
            "Select an area, then drag inside to move or along an edge to resize.\n"
            "Press Enter to lock and let clicks pass through.\n\n"
            "Ctrl+Shift+F   Select a new area\n"
            "Ctrl+Shift+E   Edit / lock the area\n"
            "Esc / Ctrl+Shift+X   Clear and return to controls\n"
            "Right-click   Clear while selecting or editing\n"
            "Alt+Tab / Ctrl+Shift+P   Show controls\n\n"
            "While editing: arrows move; Shift+arrows move faster.\n"
            "R / C changes shape; + / minus adjusts dimming.\n\n"
            "100% dimming is solid black. New selections stay editable.\n"
            "Unfinished selections cancel after 60 seconds of inactivity.\n"
            "Hold Esc for 2 seconds to quit if controls stop responding.\n"
            "Your shape and dimming are saved. Startup is always Ready."
        )
        help_text.setWordWrap(True)
        info_layout.addWidget(help_text)
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet("color: #ffcc80;")
        info_layout.addWidget(self.warning)
        dismiss = QPushButton("Close")
        dismiss.clicked.connect(self.information.accept)
        info_layout.addWidget(dismiss)
        row = QHBoxLayout()
        minimize = QPushButton("Minimize")
        minimize.clicked.connect(self.showMinimized)
        row.addWidget(minimize)
        close = QPushButton("Quit")
        close.clicked.connect(QApplication.instance().quit)
        row.addWidget(close)
        layout.addLayout(row)
        self.version_label = QLabel(APP_VERSION)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.version_label.setStyleSheet("color: #a9b9ce; font-size: 12px;")
        layout.addWidget(self.version_label)
        self.setStyleSheet("""
            QWidget { background: #101b2b; color: #edf4fc; font-family: 'Segoe UI'; font-size: 14px; }
            QPushButton { background: #213149; border: 1px solid #364961; border-radius: 7px; padding: 10px; }
            QRadioButton { padding: 8px 0; spacing: 8px; }
            QRadioButton::indicator { width: 16px; height: 16px; border: 2px solid #a9b9ce; border-radius: 9px; background: #101b2b; }
            QRadioButton::indicator:checked { background: #71d6ff; border-color: #71d6ff; }
            QPushButton:hover { background: #2d4462; }
            QPushButton#primary { background: #71d6ff; color: #102235; font-weight: bold; border: none; }
            QPushButton:disabled { color: #67768b; }
        """)
        for button in self.dim_buttons.values():
            button.ensurePolished()
            button.setMinimumWidth(button.sizeHint().width())

    def show_information(self):
        self.information.adjustSize()
        self.information.move(self.geometry().center() - self.information.rect().center())
        self.information.open()

    def closeEvent(self, event):
        QApplication.instance().quit()
        event.accept()


def app_icon():
    return QIcon(str(Path(__file__).resolve().with_name("screenspotlight.png")))


class Spotlight:
    def __init__(self, app, *, native_hotkeys=True, persist=True):
        self.app = app
        self.settings = QSettings("SpotHighlight", "ScreenSpotlight") if persist else None
        self.shape = self.settings.value("shape", "Rectangle") if self.settings else "Rectangle"
        if self.shape not in ("Rectangle", "Circle"):
            self.shape = "Rectangle"
        try:
            self.dim = max(10, min(100, int(self.settings.value("dim", 50)))) if self.settings else 50
        except (ValueError, TypeError):
            self.dim = 50
        self.dim = min(DIM_PRESETS, key=lambda value: abs(value - self.dim))
        self.mode = "off"
        self.focus = QRectF()
        self.selected_screen = None
        self.overlays = []
        self.connected_screens = set()
        self.hotkey_errors = []
        self.panel = Panel(self)
        self.icon = app_icon()
        app.setWindowIcon(self.icon)
        self.tray = QSystemTrayIcon(self.icon, self.panel)
        self.tray.setToolTip("Screen Spotlight")
        menu = QMenu(self.panel)
        for label, action in [("Show controls", self.show_panel), ("Select area", self.select),
                              ("Edit area", self.edit), ("Lock / present", self.lock),
                              ("Clear", self.clear), ("Quit", app.quit)]:
            menu.addAction(label, action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.hotkeys = Hotkeys(self) if native_hotkeys else None
        self.emergency = EmergencyExit() if native_hotkeys else None
        if self.emergency:
            self.emergency.start()
        self.escape_timer = QTimer(self.panel)
        self.escape_timer.setInterval(30)
        self.escape_timer.timeout.connect(self.poll_escape)
        self.interaction_timer = QTimer(self.panel)
        self.interaction_timer.setSingleShot(True)
        self.interaction_timer.setInterval(60000)
        self.interaction_timer.timeout.connect(self.expire_interaction)
        if self.hotkeys:
            app.installNativeEventFilter(self.hotkeys)
            for ident, key, label, callback in [(1, ord("F"), "Ctrl+Shift+F", self.select),
                                                 (2, ord("E"), "Ctrl+Shift+E", self.toggle_edit),
                                                 (5, ord("P"), "Ctrl+Shift+P", self.show_panel),
                                                 (4, ord("X"), "Ctrl+Shift+X", self.clear)]:
                if not self.hotkeys.register(ident, 0x0002 | 0x0004, key, callback):
                    self.hotkey_errors.append(label + " is unavailable (possibly used by another app).")
        self.panel.warning.setText("\n".join(self.hotkey_errors))
        self.rebuild_overlays()
        app.screenAdded.connect(self.screens_changed)
        app.screenRemoved.connect(self.screens_changed)
        app.aboutToQuit.connect(self.shutdown)

    def rebuild_overlays(self):
        for overlay in self.overlays:
            overlay.close()
            overlay.deleteLater()
        self.overlays = [Overlay(self, screen) for screen in self.app.screens()]
        for screen in self.app.screens():
            if screen not in self.connected_screens:
                screen.geometryChanged.connect(self.geometry_changed)
                self.connected_screens.add(screen)
        self.connected_screens.intersection_update(self.app.screens())

    def geometry_changed(self, *_):
        self.clear()
        for overlay in self.overlays:
            overlay.setGeometry(overlay.screen_ref.geometry())

    def screens_changed(self, *_):
        self.clear()
        self.rebuild_overlays()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_panel()

    def show_panel(self):
        self.panel.showNormal()
        self.panel.raise_()
        self.panel.activateWindow()

    def repaint(self):
        for overlay in self.overlays:
            if self.selected_screen is not None and overlay.screen_ref != self.selected_screen:
                overlay.hide()
            else:
                overlay.update()

    def set_shape(self, shape):
        self.shape = shape
        self.panel.shape_buttons[shape].setChecked(True)
        if shape == "Circle" and not self.focus.isEmpty():
            side = min(self.focus.width(), self.focus.height())
            center = self.focus.center()
            self.focus = QRectF(center.x() - side / 2, center.y() - side / 2, side, side)
        self.repaint()

    def set_dim(self, value):
        self.dim = min(DIM_PRESETS, key=lambda preset: abs(preset - value))
        self.panel.dim_buttons[self.dim].setChecked(True)
        self.panel.dim_label.setText("Background dimming")
        self.repaint()

    def step_dim(self, direction):
        index = max(0, min(len(DIM_PRESETS) - 1, DIM_PRESETS.index(self.dim) + direction))
        self.set_dim(DIM_PRESETS[index])

    def poll_escape(self):
        # Independent of focus, RegisterHotKey success, and native event delivery.
        if self.mode != "off" and self.emergency and self.emergency.key_down():
            self.clear()

    def touch_interaction(self):
        if self.mode == "select":
            self.interaction_timer.start()

    def expire_interaction(self):
        if self.mode == "select":
            self.clear()
            self.panel.status.setText("Selection cleared after 60 seconds without interaction.")

    def activate(self, mode):
        self.mode = mode
        if self.emergency:
            self.emergency.active.set()
            self.escape_timer.start()
        self.interaction_timer.stop()
        self.touch_interaction()
        if self.hotkeys:
            escape_ok = self.hotkeys.register(3, 0, 0x1B, self.clear)
            warnings = self.hotkey_errors + ([] if escape_ok else ["Esc is unavailable globally; use Ctrl+Shift+X or tray → Clear."])
            self.panel.warning.setText("\n".join(warnings))
        # Minimized normal windows remain in the taskbar and Alt+Tab.
        self.panel.information.hide()
        self.panel.showMinimized()
        for overlay in self.overlays:
            overlay.present()
        if mode in ("select", "edit"):
            screen = self.selected_screen if mode == "edit" else self.app.screenAt(QCursor.pos())
            active = next((o for o in self.overlays if o.screen_ref == screen), self.overlays[0])
            active.raise_()
            active.activateWindow()
            active.setFocus()
        self.panel.status.setText({"select": "Selecting — drag on a screen.",
                                   "edit": "Editing — move or resize, then press Enter.",
                                   "present": "Presenting — clicks pass through the spotlight."}[mode])
        # Keep a recovery control visible if Windows hotkeys or the tray are unavailable.
        if mode == "present" and (self.hotkey_errors or not QSystemTrayIcon.isSystemTrayAvailable()):
            self.show_panel()

    def select(self):
        self.focus = QRectF()
        self.selected_screen = None
        self.activate("select")

    def edit(self):
        if self.focus.isEmpty():
            self.select()
        else:
            self.activate("edit")

    def lock(self):
        if self.focus.width() >= MIN_SIZE and self.focus.height() >= MIN_SIZE:
            self.activate("present")

    def toggle_edit(self):
        if self.mode == "edit":
            self.lock()
        else:
            self.edit()

    def clear(self):
        self.mode = "off"
        self.escape_timer.stop()
        self.interaction_timer.stop()
        if self.emergency:
            self.emergency.active.clear()
        self.focus = QRectF()
        self.selected_screen = None
        for overlay in self.overlays:
            overlay.drag_start = overlay.drag_kind = None
            overlay.hide()
        if self.hotkeys:
            self.hotkeys.unregister(3)
        self.panel.warning.setText("\n".join(self.hotkey_errors))
        self.panel.status.setText("Ready — select an area to begin.")
        self.show_panel()


    def shutdown(self):
        self.escape_timer.stop()
        self.interaction_timer.stop()
        if self.emergency:
            self.emergency.stop()
        if self.hotkeys:
            self.hotkeys.close()
            self.app.removeNativeEventFilter(self.hotkeys)
        for overlay in self.overlays:
            overlay.hide()
        self.tray.hide()
        if self.settings:
            self.settings.setValue("shape", self.shape)
            self.settings.setValue("dim", self.dim)
            self.settings.sync()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Screen Spotlight")
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)
    instance_lock = QLockFile(str(Path(tempfile.gettempdir()) / "screen-spotlight.instance.lock"))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(0):
        QMessageBox.information(None, "Screen Spotlight already running",
                                "Screen Spotlight is already running, or its instance lock is unavailable.\n"
                                "Use its tray icon or Ctrl+Shift+F. A second overlay will not be started.")
        return 0
    controller = Spotlight(app)
    def handle_exception(exc_type, value, traceback):
        controller.clear()
        sys.__excepthook__(exc_type, value, traceback)
        controller.panel.status.setText(f"Spotlight cleared after an error: {value}")
        controller.show_panel()
    sys.excepthook = handle_exception
    controller.show_panel()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
