"""Standalone Windows spotlight; launch directly or as a PLAR QProcess."""
from __future__ import annotations

import ctypes
from math import atan2, hypot, pi
from ctypes import wintypes
import sys
import tempfile
from pathlib import Path

from emergency import EmergencyExit, SystemCursor
from annotations import AnnotationTools, OverlayWindow, tool_icon, set_overlay_flags

from PySide6.QtCore import (
    QAbstractNativeEventFilter, QLockFile, QPointF, QRectF, QSettings, QSize, QSizeF, Qt, QTimer, QVariantAnimation, QEasingCurve,
)
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QRegion, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QHBoxLayout, QLabel, QMenu, QPushButton, QRadioButton,
    QDialog, QGraphicsDropShadowEffect, QGroupBox, QMessageBox, QSystemTrayIcon, QSlider, QSizePolicy, QTabBar, QTabWidget, QVBoxLayout, QWidget,
)


DIM_PRESETS = (10, 20, 30, 50, 75, 85, 95, 100)
APP_VERSION = "0.1.37"
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


class Overlay(OverlayWindow):
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
        set_overlay_flags(self, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not editing)
        self.setGeometry(self.screen_ref.geometry())
        self.sync_controls_mask()
        self.setCursor(Qt.CursorShape.CrossCursor if self.controller.mode == "select" else Qt.CursorShape.ArrowCursor)
        self.show()
        self.update()

    def local_rect(self):
        return self.controller.focus.translated(-QPointF(self.geometry().topLeft()))

    def sync_controls_mask(self):
        panel = self.controller.panel
        region = QRegion(self.rect())
        if panel.isVisible() and not panel.isMinimized():
            region -= QRegion(panel.frameGeometry().translated(-self.geometry().topLeft()))
        if self.mask() != region:
            self.setMask(region)

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


class SlidingTabBar(QTabBar):
    def __init__(self):
        super().__init__()
        self.pill = QRectF()
        self.slide = QVariantAnimation(self)
        self.slide.setDuration(190)
        self.slide.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.slide.valueChanged.connect(self.set_pill)
        self.currentChanged.connect(self.move_pill)

    def set_pill(self, rect):
        self.pill = rect
        self.update()

    def move_pill(self, index):
        self.slide.stop()
        target = QRectF(self.tabRect(index)).adjusted(4, 4, -4, -4)
        if self.isVisible() and not self.pill.isEmpty():
            self.slide.setStartValue(self.pill)
            self.slide.setEndValue(target)
            self.slide.start()
        else:
            self.set_pill(target)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.slide.stop()
        self.set_pill(QRectF(self.tabRect(self.currentIndex())).adjusted(4, 4, -4, -4))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e5e8ee"))
        painter.drawRoundedRect(QRectF(self.rect()), 22, 22)
        painter.setBrush(QColor("white"))
        painter.drawRoundedRect(self.pill, 18, 18)
        for index in range(self.count()):
            painter.setPen(QColor("#535764" if index == self.currentIndex() else "#7b7f8a"))
            painter.drawText(self.tabRect(index), Qt.AlignmentFlag.AlignCenter, self.tabText(index))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#8b91a3"), 1))
            painter.drawRoundedRect(self.pill.adjusted(1, 1, -1, -1), 17, 17)


def information_icon():
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#747987"), 2.2))
    painter.drawEllipse(QRectF(7, 7, 34, 34))
    painter.setBrush(QColor("#747987"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(22, 15, 4, 4))
    painter.drawRoundedRect(QRectF(22.5, 22, 3, 11), 1.5, 1.5)
    painter.end()
    return QIcon(pixmap)


class FullWidthTabs(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabBar(SlidingTabBar())

    def sizeHint(self):
        if not self.count():
            return super().sizeHint()
        size = QSize()
        for index in range(self.count()):
            size = size.expandedTo(self.widget(index).sizeHint())
        return QSize(size.width(), size.height() + self.tabBar().sizeHint().height() + 8)

    def minimumSizeHint(self):
        return self.sizeHint()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.tabBar().setFixedWidth(self.width())
        self.tabBar().setExpanding(True)


class Panel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(WINDOW_TITLE)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(8)
        title = QLabel("Screen Spotlight")
        title.setStyleSheet("font-size: 19px; font-weight: 500;")
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        self.info_button = QPushButton("ⓘ")
        self.info_button.setText("")
        self.info_button.setIcon(information_icon())
        self.info_button.setIconSize(QSize(26, 26))
        self.info_button.setAccessibleName("Information and keyboard shortcuts")
        self.info_button.setToolTip("Information and keyboard shortcuts")
        self.info_button.setFixedSize(36, 36)
        self.info_button.clicked.connect(self.show_information)
        header.addWidget(self.info_button)
        layout.addLayout(header)
        outer_layout = layout
        self.tabs = FullWidthTabs()
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        spotlight_tab = QWidget()
        layout = QVBoxLayout(spotlight_tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(8)
        spotlight_layout = layout
        self.tabs.addTab(spotlight_tab, "Spotlight")
        controller.annotations = AnnotationTools(controller)
        self.tabs.addTab(controller.annotations, "Annotation")
        self.tabs.setTabToolTip(0, "Spotlight: select an area and dim its surroundings")
        self.tabs.setTabToolTip(1, "Annotation: start drawing with the selected tool")
        outer_layout.addWidget(self.tabs)
        shape_box = QGroupBox("Highlight shape")
        layout.addWidget(shape_box)
        self.shape_group = QButtonGroup(self)
        self.shape_buttons = {}
        shape_row = QHBoxLayout(shape_box)
        for name in ("Rectangle", "Circle"):
            button = QPushButton(name)
            button.setCheckable(True)
            button.setObjectName("rectangleChoice" if name == "Rectangle" else "circleChoice")
            button.setFixedHeight(42)
            self.shape_group.addButton(button)
            self.shape_buttons[name] = button
            button.setChecked(name == controller.shape)
            shape_row.addWidget(button)
        self.shape_group.buttonClicked.connect(lambda button: controller.set_shape(button.text()))
        dim_box = QGroupBox("Background dimming")
        layout.addWidget(dim_box)
        dim_layout = QVBoxLayout(dim_box)
        self.dim_label = QLabel(str(controller.dim))
        self.dim_label.setObjectName("dimValue")
        self.dim_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        value_row = QHBoxLayout()
        value_row.setSpacing(0)
        value_row.addWidget(self.dim_label)
        self.dim_percent = QLabel("%")
        self.dim_percent.setStyleSheet("font-size: 14px; color: #868b97; padding-bottom: 4px;")
        value_row.addWidget(self.dim_percent, alignment=Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch()
        dim_layout.addLayout(value_row)
        self.dim_slider = QSlider(Qt.Orientation.Horizontal)
        self.dim_slider.setRange(10, 100)
        self.dim_slider.setValue(controller.dim)
        self.dim_slider.setAccessibleName("Background dimming percentage")
        self.dim_slider.valueChanged.connect(controller.set_dim)
        dim_layout.addWidget(self.dim_slider)
        ends = QHBoxLayout()
        for text in ("Subtle", "Full focus"):
            label = QLabel(text)
            label.setObjectName("rangeCaption")
            if text == "Full focus":
                label.setAlignment(Qt.AlignmentFlag.AlignRight)
            ends.addWidget(label)
        dim_layout.addLayout(ends)
        self.dim_group = QButtonGroup(self)
        self.dim_buttons = {}
        dim_row = QHBoxLayout()
        dim_row.setSpacing(5)
        dim_layout.addLayout(dim_row)
        for value in DIM_PRESETS:
            button = QPushButton(f"{value}%")
            button.setCheckable(True)
            button.setObjectName("dimPreset")
            self.dim_group.addButton(button, value)
            self.dim_buttons[value] = button
            button.setChecked(value == controller.dim)
            dim_row.addWidget(button)
        self.dim_group.idClicked.connect(controller.set_dim)
        area_box = QGroupBox("Your spotlight")
        layout.addWidget(area_box)
        layout = QVBoxLayout(area_box)
        select = QPushButton("Select area")
        select.setObjectName("primary")
        select.setFixedHeight(42)
        select.clicked.connect(controller.select)
        layout.addWidget(select)
        row = QHBoxLayout()
        for label, action in [("Move / resize", controller.edit), ("Lock / present", controller.lock), ("Clear", controller.clear)]:
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        for section_layout in (shape_row, dim_layout, layout):
            section_layout.setContentsMargins(16, 12, 16, 14)

        spotlight_layout.addStretch()
        layout = outer_layout
        self.status = controller.annotations.status
        self.status.setText("Ready — select an area to begin.")
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
            "Annotation: click a tool to start drawing. Controls stay available.\n"
            "Annotations stay pinned to their screen when controls move.\n"
            "Move to this screen: confirm moving the area, keeping all marks.\n"
            "Clear annotations resets marks and numbering; Undo restores them.\n"
            "Esc / Enter ends drawing and keeps the marks.\n"
            "Ctrl+Z / Ctrl+Y undoes / redoes while drawing.\n"
            "Move: drag any mark; click then use arrows (Shift = 10 pixels).\n"
            "Right-click a grouped tool or use its arrow to see variants with icons.\n"
            "Horizontal highlighter: Shift makes the line vertical.\n"
            "Rectangle / filled rectangle: Shift makes a square.\n"
            "Laser: dot only; cursor returns over controls and when laser stops.\n"
            "Esc or Pointer stops the laser. Capture Image copies a fresh screenshot.\n"
            "Save Image captures a fresh screenshot and opens the save dialog.\n"
            "Capture defaults to the spotlight area, or the monitor if no area exists.\n\n"
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
        self.warning.setStyleSheet("color: #8a4c16;")
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
        self.version_label.setStyleSheet("color: #707684; font-size: 12px;")
        layout.addWidget(self.version_label)
        self.setObjectName("porcelainPanel")
        self.status.setObjectName("activityStatus")
        self.info_button.setObjectName("informationButton")
        self.setStyleSheet("""
            QWidget { color: #454551; font-family: 'Segoe UI'; font-size: 13px; }
            QWidget#porcelainPanel, QDialog { background: #ffffff; }
            QLabel, QRadioButton { background: transparent; }
            QPushButton { background: #ffffff; color: #737783; font-size: 12px; border: 1px solid #d8dce4;
                          border-radius: 17px; padding: 9px 12px; }
            QPushButton:hover { background: #edf0f5; border-color: #b6bfce; }
            QPushButton:pressed { background: #dfe4ed; }
            QPushButton[checkable="true"] { background: #e5e8ee; border: 1px solid transparent; }
            QPushButton:checked { background: #ffffff; color: #535764; border: 1px solid transparent; }
            QPushButton:checked:hover { background: #ffffff; }
            QWidget#segmentedChoices { background: #e5e8ee; border-radius: 17px; }
            QPushButton#segmentChoice { background: transparent; border: 1px solid transparent;
                                        border-radius: 14px; padding: 6px 10px; font-size: 11px; }
            QPushButton#segmentChoice:checked { background: #ffffff; color: #535764; }
            QPushButton#segmentChoice:disabled { background: transparent; color: #9a9fab; }
            QPushButton:focus { border: 1px dotted #a5adbd; }
            QPushButton[checkable="true"]:focus { border: 1px solid #ffffff; }
            QSpinBox:focus { border: none; }
            QPushButton#primary { background: #4f5463; color: #ffffff; font-weight: 600;
                                 border: 1px solid #4f5463; border-radius: 20px; }
            QPushButton#primary:hover { background: #3f4452; }
            QPushButton#primary:pressed { background: #303542; }
            QPushButton#primary:focus { border: 2px solid #adb9d2; }
            QPushButton#informationButton { border: none; background: transparent; padding: 0; }
            QPushButton:disabled { background: #f3f4f6; color: #9197a3; border-color: #e5e7ec; }
            QRadioButton { padding: 8px 0; spacing: 8px; }
            QRadioButton::indicator { width: 14px; height: 14px; border: 2px solid #a1a8b6;
                                     border-radius: 9px; background: #ffffff; }
            QRadioButton::indicator:checked { background: #697186; border-color: #697186; }
            QRadioButton::indicator:hover { border-color: #454b5b; }
            QRadioButton:focus { color: #303542; text-decoration: underline; }
            QRadioButton:disabled { color: #9197a3; }
            QRadioButton::indicator:disabled { background: #eef0f4; border-color: #d8dce4; }
            QTabWidget::pane { border: none; background: #ffffff; }
            QTabBar { background: #f0f1f4; border-radius: 22px; }
            QTabBar::tab { background: transparent; color: #707684; padding: 11px 16px;
                           border: 3px solid #f0f1f4; border-radius: 22px; font-size: 13px; }
            QTabBar::tab:selected { background: #ffffff; color: #454551; }
            QTabBar::tab:hover { color: #303542; background: #e9ecf2; }
            QGroupBox { background: #eef0f4; font-size: 12px; font-weight: 700;
                        border: 1px solid #e9ecf1; border-radius: 12px; margin-top: 0; padding-top: 24px; }
            QGroupBox::title { subcontrol-origin: border; subcontrol-position: top left;
                              top: 10px; left: 17px; color: #555d70; }
            QPushButton#rectangleChoice { border-radius: 6px; background: #e5e8ee; }
            QPushButton#circleChoice { border-radius: 21px; background: #e5e8ee; }
            QPushButton#rectangleChoice:checked, QPushButton#circleChoice:checked { background: #ffffff; color: #535764; border: 1px solid transparent; }
            QPushButton#dimPreset { background: #e0e4ec; border: 1px solid transparent;
                                   border-radius: 12px; padding: 5px 2px; font-size: 11px; }
            QPushButton#dimPreset:checked { background: #ffffff; border-color: transparent; color: #535764; }
            QPushButton#dimPreset:focus { border-color: #697186; }
            QLabel#dimValue { font-size: 30px; font-weight: 400; }
            QLabel#rangeCaption { color: #707684; font-size: 11px; }
            QSlider { background: transparent; min-height: 24px; }
            QSlider::groove:horizontal { height: 5px; background: #dfe3eb; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #697186; border-radius: 2px; }
            QSlider::handle:horizontal { background: #697186; width: 14px; margin: -5px 0;
                                        border-radius: 7px; }
            QSlider::handle:horizontal:focus { background: #454b5b; }
            QGroupBox QRadioButton { padding: 2px 0; }
            QSpinBox { background: #ffffff; color: #454551; border: 1px solid #d8dce4;
                       border-radius: 12px; padding: 4px 8px; min-height: 20px;
                       selection-background-color: #eef0f4; selection-color: #454551; }
            QLabel#activityStatus { background: #f0f1f4; color: #626a7c;
                                    border-radius: 14px; padding: 8px 10px; font-size: 11px; }
            QToolTip { background: #ffffff; color: #454551; border: 1px solid #c5cbd6; padding: 6px; }
        """)
        # Keep elevation inside the controls; screen overlays retain their exact geometry.
        for section in self.findChildren(QGroupBox):
            shadow = QGraphicsDropShadowEffect(section)
            shadow.setBlurRadius(12)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(63, 72, 91, 16))
            section.setGraphicsEffect(shadow)
        for button in self.dim_buttons.values():
            button.ensurePolished()
            button.setMinimumWidth(button.sizeHint().width())
        # Include initially hidden tools when measuring the shared panel size.
        self.ensurePolished()
        for widget in self.findChildren(QWidget):
            widget.ensurePolished()
        # Reserve two status lines so changing activity text cannot resize the panel.
        self.status.ensurePolished()
        self.status.setMinimumHeight(self.status.fontMetrics().lineSpacing() * 2 + 16)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.resize(self.minimumWidth(), self.sizeHint().height())

    def tab_changed(self, index):
        annotations = self.controller.annotations
        annotations.sync_capture_scope()
        if index == 0:
            if annotations.drawing:
                annotations.interact()
            self.status.setText({"off": "Ready", "select": "Selecting spotlight area",
                                 "edit": "Editing spotlight area", "present": "Presenting spotlight"}[self.controller.mode])
        elif not annotations.drawing:
            annotations.start()

    def show_information(self):
        if self.controller.annotations.drawing:
            self.controller.annotations.interact()
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
        self.mode = "off"
        self.escape_held = False
        self.focus = QRectF()
        self.selected_screen = None
        self.overlays = []
        self.connected_screens = set()
        self.hotkey_errors = []
        self.system_cursor = SystemCursor(enabled=app.platformName() == "windows")
        self.panel = Panel(self)
        self.panel.installEventFilter(self.annotations.overlay)
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
        self.emergency = EmergencyExit(cleanup=self.system_cursor.restore) if native_hotkeys else None
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
        screens = self.app.screens()
        existing = {overlay.screen_ref: overlay for overlay in self.overlays}
        for screen, overlay in existing.items():
            if screen not in screens:
                overlay.close()
                overlay.deleteLater()
        self.overlays = [existing[screen] if screen in existing else Overlay(self, screen) for screen in screens]
        for screen in screens:
            if screen not in self.connected_screens:
                screen.geometryChanged.connect(self.geometry_changed)
                self.connected_screens.add(screen)
        self.connected_screens.intersection_update(self.app.screens())

    def geometry_changed(self, *_):
        screens = self.app.screens()
        self.annotations.sync_screen(screens)
        if self.selected_screen is not None and self.selected_screen not in screens:
            self.clear()
            return
        selected_overlay = next((o for o in self.overlays if o.screen_ref == self.selected_screen), None)
        if selected_overlay is not None and not self.focus.isEmpty():
            old = selected_overlay.geometry()
            bounds = self.selected_screen.geometry()
            if old != bounds:
                # A layout notification must not delete a valid area. Translate its
                # monitor-relative position, then fit it within the new bounds.
                rect = QRectF(self.focus).translated(QPointF(bounds.topLeft() - old.topLeft()))
                width = min(rect.width(), bounds.width())
                height = min(rect.height(), bounds.height())
                if self.shape == "Circle":
                    width = height = min(width, height)
                rect.setSize(QSizeF(width, height))
                self.focus = move_rect(rect, QPointF(), QRectF(bounds))
        for overlay in self.overlays:
            if overlay.screen_ref not in screens:
                continue
            bounds = overlay.screen_ref.geometry()
            if overlay.geometry() != bounds:
                overlay.drag_start = overlay.drag_kind = None
                overlay.setGeometry(bounds)
                overlay.sync_controls_mask()
        self.repaint()

    def screens_changed(self, *_):
        # Connecting or removing an unrelated monitor must not clear this monitor.
        self.geometry_changed()
        existing = set(self.overlays)
        self.rebuild_overlays()
        if self.mode != "off":
            for overlay in self.overlays:
                if overlay not in existing:
                    overlay.present()
        self.annotations.overlay.sync_controls_mask()
        self.repaint()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_panel()

    def show_panel(self):
        self.panel.showNormal()
        self.panel.raise_()
        self.panel.activateWindow()
        self.annotations.sync_capture_scope()
        self.annotations.overlay.sync_controls_mask()

    def repaint(self):
        self.annotations.sync_capture_scope()
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
        self.dim = max(10, min(100, int(value)))
        panel = self.panel
        panel.dim_slider.blockSignals(True)
        panel.dim_slider.setValue(self.dim)
        panel.dim_slider.blockSignals(False)
        panel.dim_group.setExclusive(False)
        for preset, button in panel.dim_buttons.items():
            button.setChecked(preset == self.dim)
        panel.dim_group.setExclusive(True)
        panel.dim_label.setText(str(self.dim))
        self.repaint()

    def step_dim(self, direction):
        if direction > 0:
            value = next((preset for preset in DIM_PRESETS if preset > self.dim), 100)
        else:
            value = next((preset for preset in reversed(DIM_PRESETS) if preset < self.dim), 10)
        self.set_dim(value)

    def poll_escape(self):
        # Independent of focus, RegisterHotKey success, and native event delivery.
        down = bool(self.emergency and self.emergency.key_down())
        if down and not self.escape_held:
            self.escape()
        self.escape_held = down

    def escape(self):
        down = bool(self.emergency and self.emergency.key_down())
        if down and self.escape_held:
            return
        self.escape_held = down
        if self.annotations.drawing:
            self.annotations.interact()
        elif self.mode != "off":
            self.clear()

    def disarm_escape(self):
        self.escape_timer.stop()
        if self.emergency:
            self.emergency.active.clear()
        if self.hotkeys:
            self.hotkeys.unregister(3)

    def arm_escape(self):
        if not self.escape_timer.isActive():
            self.escape_held = False
        if self.emergency:
            self.emergency.active.set()
            self.escape_timer.start()
        if self.hotkeys:
            escape_ok = self.hotkeys.register(3, 0, 0x1B, self.escape)
            warnings = self.hotkey_errors + ([] if escape_ok else ["Esc is unavailable globally; use Ctrl+Shift+X."])
            self.panel.warning.setText("\n".join(warnings))

    def touch_interaction(self):
        if self.mode == "select":
            self.interaction_timer.start()

    def expire_interaction(self):
        if self.mode == "select":
            self.clear()
            self.panel.status.setText("Selection cleared after 60 seconds without interaction.")

    def activate(self, mode, *, keep_controls=False):
        if self.annotations.drawing:
            self.annotations.interact()
        self.mode = mode
        self.arm_escape()
        self.interaction_timer.stop()
        self.touch_interaction()
        if self.hotkeys:
            escape_ok = self.hotkeys.register(3, 0, 0x1B, self.escape)
            warnings = self.hotkey_errors + ([] if escape_ok else ["Esc is unavailable globally; use Ctrl+Shift+X or tray → Clear."])
            self.panel.warning.setText("\n".join(warnings))
        # Minimized normal windows remain in the taskbar and Alt+Tab.
        self.panel.information.hide()
        if mode == "select" and not keep_controls:
            self.panel.showMinimized()
        else:
            self.panel.showNormal()
        for overlay in self.overlays:
            overlay.present()
        if self.annotations.screen and self.annotations.marks:
            self.annotations.overlay.raise_()
        if mode in ("select", "edit"):
            screen = self.selected_screen if mode == "edit" else self.app.screenAt(QCursor.pos())
            active = next((o for o in self.overlays if o.screen_ref == screen), self.overlays[0])
            active.raise_()
            active.activateWindow()
            active.setFocus()
        if mode != "select":
            self.panel.raise_()
            self.annotations.overlay.sync_controls_mask()
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
        if self.annotations.drawing:
            self.annotations.interact()
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
        self.annotations.overlay.hide()
        self.system_cursor.close()
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
