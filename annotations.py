"""Screen-space annotation tools and capture controls."""
from dataclasses import dataclass, field, replace
from functools import lru_cache
from math import atan2, cos, sin, pi
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, QTimer, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap, QRadialGradient, QRegion, QValidator
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMenu, QPushButton, QRadioButton, QSizePolicy, QSpinBox, QToolTip, QVBoxLayout, QWidget,
)


PALETTES = (
    ("#e53935", "#f58220", "#ffdc32", "#28b463", "#00bcd4", "#3265e8", "#a980ed", "#212121"),
    ("#f5a6a3", "#ffc49a", "#fff0a3", "#a5dfb5", "#a0e4ec", "#afc4fa", "#c8aff5", "#212121"),
)
COLOR_NAMES = ("Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Purple", "Black")


TOOL_DESCRIPTIONS = {
    "Pen": "Pen: draw freehand strokes",
    "Highlighter": "Highlighter: draw translucent strokes",
    "Horizontal highlighter": "Horizontal highlighter: drag a straight horizontal highlight; hold Shift for a vertical line",
    "Laser pointer": "Laser pointer: show only a temporary laser dot; adjust Laser size and Color; clicks pass through; Esc or Pointer stops it",
    "Filled rectangle": "Filled rectangle: drag a solid area in the selected color; hold Shift for a square",
    "Filled circle": "Filled circle: drag a solid circle in the selected color",
    "Arrow": "Arrow: drag to point at something",
    "Rectangle": "Rectangle: drag to outline an area; hold Shift for a square",
    "Circle": "Circle: drag to circle an area",
    "Number": "Numbered marker: click to place the next number",
    "Letter": "Lettered marker: click to place the next letter",
    "Eraser": "Eraser: click an annotation to remove it",
    "Move annotations": "Move annotations: drag a mark to move it; click to select, then use arrows (Shift for 10 pixels)",
    "Undo": "Undo: reverse the last annotation change",
    "Redo": "Redo: restore the last undone change",
    "Clear annotations": "Clear annotations: erase all marks",
    "Interact with desktop": "Interact with desktop: stop drawing and use the app underneath; keep annotations visible",
    "Capture screen": "Capture: capture the chosen area with annotations",
    "Capture and copy": "Capture and copy: take a fresh capture of the chosen area and copy it directly to the clipboard",
    "Save PNG": "Save the latest capture as a PNG image (capture first)",
}


class ThinArrow(QPushButton):
    def __init__(self, up, parent):
        super().__init__(parent)
        self.up = up
        self.setAccessibleName("Increase" if up else "Decrease")
        self.setAutoRepeat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(24, 18)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = "#454551" if self.underMouse() or self.hasFocus() else "#858894"
        painter.setPen(QPen(QColor(color), 1.1, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        x, y = self.width() / 2, self.height() / 2
        sign = -1 if self.up else 1
        path = QPainterPath(QPointF(x - 4, y - sign * 2))
        path.lineTo(x, y + sign * 2)
        path.lineTo(x + 4, y - sign * 2)
        painter.drawPath(path)


class SlimSpinBox(QSpinBox):
    """Editable number with real repeatable buttons and lightweight chevrons."""
    def __init__(self):
        super().__init__()
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(112, 38)
        self.setStyleSheet("QSpinBox { background: transparent; border: none; padding: 0 24px; font-size: 22px; color: #454551; } QSpinBox:focus { border: none; } QLineEdit { background: transparent; selection-background-color: #eef0f4; selection-color: #454551; }")
        self.up_arrow = ThinArrow(True, self)
        self.down_arrow = ThinArrow(False, self)
        self.up_arrow.clicked.connect(self.stepUp)
        self.down_arrow.clicked.connect(self.stepDown)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.up_arrow.move(self.width() - 24, 1)
        self.down_arrow.move(self.width() - 24, 19)


class ColorSwatch(QPushButton):
    def __init__(self):
        super().__init__()
        self.color = QColor("white")
        self.setFixedSize(34, 34)
        self.setCheckable(True)
        self.fade = QVariantAnimation(self)
        self.fade.setDuration(180)
        self.fade.valueChanged.connect(self.set_display_color)

    def set_display_color(self, color):
        self.color = color
        self.update()

    def set_color(self, color):
        self.fade.stop()
        self.fade.setStartValue(self.color)
        self.fade.setEndValue(QColor(color))
        if self.isVisible():
            self.fade.start()
        else:
            self.set_display_color(QColor(color))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.color)
        painter.setPen(QPen(QColor("white"), 1.5))
        painter.drawEllipse(QRectF(self.rect()).adjusted(2, 2, -2, -2))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("white"), 1))
            painter.drawEllipse(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5))


class SwatchTrack(QWidget):
    """A selection outline that slides without changing when the color takes effect."""
    def __init__(self, group):
        super().__init__()
        self.group = group
        self.outline = QRectF()
        self.slide = QVariantAnimation(self)
        self.slide.setDuration(190)
        self.slide.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.slide.valueChanged.connect(self.set_outline)
        group.idToggled.connect(lambda index, checked: self.retarget() if checked else None)

    def set_outline(self, rect):
        self.outline = rect
        self.update()

    def retarget(self, animate=True):
        button = self.group.checkedButton()
        if button is None:
            return
        target = QRectF(button.geometry()).adjusted(-1, -1, 1, 1)
        self.slide.stop()
        if animate and self.isVisible() and not self.outline.isEmpty():
            self.slide.setStartValue(self.outline)
            self.slide.setEndValue(target)
            self.slide.start()
        else:
            self.set_outline(target)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, lambda: self.retarget(False))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, lambda: self.retarget(False))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(self.outline)


def load_tool_pixmap(name):
    return QPixmap(str(Path(__file__).resolve().parent / "icons" / name))


@lru_cache(maxsize=32)
def tool_icon(name):
    pixmap = load_tool_pixmap(name)
    pixmap = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    icon = QIcon(pixmap)
    icon.addPixmap(pixmap, QIcon.Mode.Disabled)
    return icon


def marker_label(number, letters=False):
    if not letters:
        return str(number)
    label = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        label = chr(65 + remainder) + label
    return label


class MarkerSequence(SlimSpinBox):
    def __init__(self):
        self.letters = False
        super().__init__()

    def set_letters(self, letters):
        self.interpretText()
        self.letters = letters
        self.lineEdit().setText(self.textFromValue(self.value()))

    def textFromValue(self, value):
        return marker_label(value, True) if self.letters else str(value)

    def valueFromText(self, text):
        if not self.letters:
            return super().valueFromText(text)
        value = 0
        for letter in text.strip().upper():
            value = value * 26 + ord(letter) - ord("A") + 1
        return value

    def validate(self, text, pos):
        if not self.letters:
            return super().validate(text, pos)
        text = text.upper()
        if not text:
            state = QValidator.State.Intermediate
        elif all("A" <= letter <= "Z" for letter in text) and self.minimum() <= self.valueFromText(text) <= self.maximum():
            state = QValidator.State.Acceptable
        else:
            state = QValidator.State.Invalid
        return state, text, pos


@dataclass
class Mark:
    tool: str
    color: str
    width: int
    size: int
    points: list = field(default_factory=list)
    label: str = ""

    def path(self):
        path = QPainterPath()
        start, end = self.points[0], self.points[-1]
        rect = QRectF(start, end).normalized()
        if self.tool in ("number", "letter"):
            path.addEllipse(start, self.size / 2, self.size / 2)
        elif self.tool in ("rectangle", "filled_rectangle"):
            path.addRect(rect)
        elif self.tool in ("circle", "filled_circle"):
            path.addEllipse(rect)
        else:
            path.moveTo(start)
            for point in self.points[1:]:
                path.lineTo(point)
            if len(self.points) == 1 or start == end:
                path.lineTo(start + QPointF(0.01, 0))
            if self.tool == "arrow" and start != end:
                angle = atan2(end.y() - start.y(), end.x() - start.x())
                length = max(14, self.width * 4)
                for offset in (-pi / 6, pi / 6):
                    path.moveTo(end)
                    path.lineTo(end - QPointF(cos(angle + offset) * length, sin(angle + offset) * length))
        return path

    def translated(self, delta):
        return replace(self, points=[point + delta for point in self.points])

    def hit(self, point, interior=False):
        path = self.path()
        stroke = QPainterPathStroker()
        stroke.setWidth(max(12, self.width))
        return stroke.createStroke(path).contains(point) or (
            (bool(self.label) or self.tool in ("filled_rectangle", "filled_circle") or (
                interior and self.tool in ("rectangle", "circle"))) and path.contains(point))

    def paint(self, painter):
        painter.save()
        color = QColor(self.color)
        if self.tool in ("highlighter", "horizontal_highlighter"):
            color.setAlpha(90)
        painter.setPen(QPen(color, self.width, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(color if self.label or self.tool in ("filled_rectangle", "filled_circle")
                         else Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())
        if self.label:
            luminance = color.redF() * .2126 + color.greenF() * .7152 + color.blueF() * .0722
            painter.setPen(QColor("#101010" if luminance > .5 else "#ffffff"))
            font = QFont("Segoe UI")
            font.setBold(True)
            font.setPixelSize(round(self.size * .52))
            painter.setFont(font)
            while painter.fontMetrics().horizontalAdvance(self.label) > self.size * .8 and font.pixelSize() > 6:
                font.setPixelSize(font.pixelSize() - 1)
                painter.setFont(font)
            p = self.points[0]
            painter.drawText(QRectF(p.x() - self.size / 2, p.y() - self.size / 2,
                                    self.size, self.size), Qt.AlignmentFlag.AlignCenter, self.label)
        painter.restore()


def set_overlay_flags(widget, flags):
    """Update a visible native overlay without QWidget's hide/show transition."""
    window = widget.windowHandle()
    if widget.isVisible() and window is not None and QApplication.platformName() == "windows":
        window.setFlags(flags)
    else:
        widget.setWindowFlags(flags)


class InkOverlay(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.pending = None
        self.reset_edit()
        self.laser_point = None
        self.laser_timer = QTimer(self)
        self.laser_timer.setInterval(16)
        self.laser_timer.timeout.connect(self.track_laser)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setWindowTitle("Screen Spotlight annotations")

    def present(self, drawing):
        self.pending = None
        self.reset_edit()
        self.stop_laser()
        laser = drawing and self.owner.tool == "laser"
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        if not drawing or laser:
            flags |= Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus
        set_overlay_flags(self, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not drawing or laser)
        self.setGeometry(self.owner.screen.geometry())
        self.setCursor(Qt.CursorShape.ArrowCursor if self.owner.tool == "move" else Qt.CursorShape.CrossCursor)
        self.sync_controls_mask()
        self.show()
        self.raise_()
        if laser:
            self.laser_timer.start()
            self.track_laser()
        elif drawing:
            self.activateWindow()
            self.setFocus()

    def stop_laser(self):
        self.owner.controller.system_cursor.restore()
        self.laser_timer.stop()
        self.laser_point = None
        self.update()

    def hideEvent(self, event):
        self.stop_laser()
        super().hideEvent(event)

    def track_laser(self):
        if not self.owner.drawing or self.owner.tool != "laser":
            self.stop_laser()
            return
        point = self.mapFromGlobal(QCursor.pos())
        point = QPointF(point) if self.rect().contains(point) and self.mask().contains(point) else None
        # Repaint only the old and new glow bounds, including live size changes.
        radius = self.owner.laser_size.maximum()
        previous = self.laser_point
        self.laser_point = point
        self.owner.controller.system_cursor.set_hidden(point is not None)
        for position in (previous, point):
            if position is not None:
                self.update(QRectF(position.x() - radius, position.y() - radius,
                                   radius * 2, radius * 2).toAlignedRect())

    def paint_laser(self, painter):
        if self.laser_point is None:
            return
        color = QColor(PALETTES[self.owner.variant.checkedId()][self.owner.color])
        radius = self.owner.laser_size.value() / 2
        glow = QRadialGradient(self.laser_point, radius * 1.8)
        glow.setColorAt(0, QColor("white"))
        glow.setColorAt(.22, color.lighter(150))
        glow.setColorAt(.5, color)
        glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(self.laser_point, radius * 1.8, radius * 1.8)

    def sync_controls_mask(self):
        panel = self.owner.controller.panel
        region = QRegion(self.rect())
        if panel.isVisible() and not panel.isMinimized():
            frame = panel.frameGeometry().translated(-self.geometry().topLeft())
            region -= QRegion(frame)
        self.setMask(region)
        for overlay in self.owner.controller.overlays:
            overlay.sync_controls_mask()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show,
                            QEvent.Type.Hide, QEvent.Type.WindowStateChange):
            self.sync_controls_mask()
        return super().eventFilter(watched, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1 if self.owner.drawing and self.owner.tool != "laser" else 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        for mark in self.owner.marks:
            mark.paint(painter)
        if self.pending:
            self.pending.paint(painter)
        self.paint_laser(painter)
        if self.owner.drawing and self.owner.tool == "move" and self.selected_index is not None:
            bounds = self.owner.marks[self.selected_index].path().boundingRect().adjusted(-5, -5, 5, 5)
            painter.setPen(QPen(QColor("#3265e8"), 1.2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(bounds)

    def reset_edit(self):
        self.selected_index = None
        self.move_start = None
        self.move_original = None
        self.move_saved = False
        self.update()

    def mark_at(self, point):
        return next((i for i in range(len(self.owner.marks) - 1, -1, -1)
                     if self.owner.marks[i].hit(point, interior=True)), None)

    def constrain_delta(self, mark, delta):
        bounds = mark.path().boundingRect()
        return QPointF(max(-bounds.left(), min(delta.x(), self.width() - bounds.right())),
                       max(-bounds.top(), min(delta.y(), self.height() - bounds.bottom())))

    def drag_mark(self, point):
        requested = point - self.move_start
        delta = self.constrain_delta(self.move_original, requested) if not requested.isNull() else QPointF()
        if not delta.isNull() or self.move_saved:
            if not self.move_saved:
                self.owner.remember()
                self.move_saved = True
            self.owner.marks[self.selected_index] = self.move_original.translated(delta)
            self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.owner.drawing:
            return
        owner = self.owner
        if owner.tool == "laser":
            return
        point = event.position()
        if owner.tool == "move":
            self.selected_index = self.mark_at(point)
            if self.selected_index is not None:
                self.move_start = QPointF(point)
                self.move_original = owner.marks[self.selected_index]
                self.move_saved = False
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            return
        if owner.tool == "eraser":
            for i in range(len(owner.marks) - 1, -1, -1):
                if owner.marks[i].hit(point):
                    owner.remember()
                    del owner.marks[i]
                    self.update()
                    break
            return
        mark = Mark(owner.tool, PALETTES[owner.variant.checkedId()][owner.color],
                    owner.width.value(), owner.size.value(), [point])
        if owner.tool in ("number", "letter"):
            mark.label = marker_label(owner.sequence.value(), owner.tool == "letter")
            owner.remember()
            owner.marks.append(mark)
            owner.sequence.setValue(owner.sequence.value() + 1)
        else:
            self.pending = mark
        self.update()

    def mouseMoveEvent(self, event):
        if self.owner.drawing and self.owner.tool == "move":
            if self.move_start is not None:
                self.drag_mark(event.position())
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor if self.mark_at(event.position()) is not None
                               else Qt.CursorShape.ArrowCursor)
            return
        if self.pending:
            point = event.position()
            point = QPointF(max(0, min(point.x(), self.width())), max(0, min(point.y(), self.height())))
            if self.pending.tool in ("pen", "highlighter"):
                self.pending.points.append(point)
            else:
                if self.pending.tool == "horizontal_highlighter":
                    start = self.pending.points[0]
                    point = (QPointF(start.x(), point.y()) if event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                             else QPointF(point.x(), start.y()))
                elif self.pending.tool in ("circle", "filled_circle") or (
                        self.pending.tool in ("rectangle", "filled_rectangle") and
                        event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    start = self.pending.points[0]
                    delta = point - start
                    side = min(abs(delta.x()), abs(delta.y()))
                    point = start + QPointF(side if delta.x() >= 0 else -side,
                                           side if delta.y() >= 0 else -side)
                self.pending.points = [self.pending.points[0], point]
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.move_start is not None:
            self.drag_mark(event.position())
            self.move_start = self.move_original = None
            self.move_saved = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton and self.pending:
            self.mouseMoveEvent(event)
            self.owner.remember()
            self.owner.marks.append(self.pending)
            self.pending = None
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.owner.controller.escape()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.owner.interact()
        elif self.owner.tool == "move" and self.selected_index is not None and event.key() in (
                Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx, dy = {Qt.Key.Key_Left: (-step, 0), Qt.Key.Key_Right: (step, 0),
                      Qt.Key.Key_Up: (0, -step), Qt.Key.Key_Down: (0, step)}[event.key()]
            mark = self.owner.marks[self.selected_index]
            delta = self.constrain_delta(mark, QPointF(dx, dy))
            if not delta.isNull():
                self.owner.remember()
                self.owner.marks[self.selected_index] = mark.translated(delta)
                self.update()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.owner.undo()
            elif event.key() == Qt.Key.Key_Y:
                self.owner.redo()


class IconButton(QPushButton):
    """Show hover help even while the separate drawing window owns focus."""
    def __init__(self):
        super().__init__()
        self.tool_menu = None
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(450)
        self.hover_timer.timeout.connect(self.show_hover_help)

    def enterEvent(self, event):
        self.hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_timer.stop()
        QToolTip.hideText()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.hover_timer.stop()
        QToolTip.hideText()
        if self.tool_menu and (event.button() == Qt.MouseButton.RightButton or (
                event.button() == Qt.MouseButton.LeftButton and event.position().x() >= self.width() - 20)):
            self.show_tool_menu()
            event.accept()
            return
        super().mousePressEvent(event)

    def show_tool_menu(self):
        self.hover_timer.stop()
        QToolTip.hideText()
        self.tool_menu.popup(self.mapToGlobal(self.rect().bottomLeft()))

    def contextMenuEvent(self, event):
        if self.tool_menu:
            if not self.tool_menu.isVisible():
                self.show_tool_menu()
            event.accept()
        else:
            super().contextMenuEvent(event)

    def keyPressEvent(self, event):
        if self.tool_menu and (event.key() == Qt.Key.Key_Menu or (
                event.key() == Qt.Key.Key_F10 and event.modifiers() & Qt.KeyboardModifier.ShiftModifier) or (
                event.key() == Qt.Key.Key_Down and event.modifiers() & Qt.KeyboardModifier.AltModifier)):
            self.show_tool_menu()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.tool_menu:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#737783"), 1.2, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            x, y = self.width() - 12, self.height() / 2
            path = QPainterPath(QPointF(x - 3, y - 1.5))
            path.lineTo(x, y + 1.5)
            path.lineTo(x + 3, y - 1.5)
            painter.drawPath(path)

    def show_hover_help(self):
        if self.isVisible() and self.underMouse():
            QToolTip.showText(QCursor.pos(), self.toolTip(), self, self.rect(), 6000)


class AnnotationTools(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.tool = "pen"
        self.tool_widths = {}
        self.color = 0
        self.screen = None
        self.drawing = False
        self.marks = []
        self.history = []
        self.future = []
        self.captured = QPixmap()
        self.capturing = False
        self.overlay = InkOverlay(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(8)
        tools_box = QGroupBox("Tools")
        tools_layout = QVBoxLayout(tools_box)
        layout.addWidget(tools_box)
        grid = QGridLayout()
        self.tools = QButtonGroup(self)
        self.tool_buttons = {}
        self.tool_actions = {}
        self.tool_specs = {
            "pen": ("Pen", "02 Pen.png"),
            "move": ("Move annotations", "13 Mouse Pointer.png"),
            "highlighter": ("Highlighter", "03 Highlighter.png"),
            "horizontal_highlighter": ("Horizontal highlighter", "21 Horizontal Highlighter.png"),
            "laser": ("Laser pointer", "22 Laser Pointer.png"),
            "arrow": ("Arrow", "04 Arrow.png"),
            "rectangle": ("Rectangle", "05 Rectangle.png"),
            "filled_rectangle": ("Filled rectangle", "23 Filled Rectangle.png"),
            "circle": ("Circle", "06 Circle.png"),
            "filled_circle": ("Filled circle", "24 Filled Circle.png"),
            "number": ("Number", "07 Numbered Marker.png"),
            "letter": ("Letter", "08 Lettered Marker.png"),
            "eraser": ("Eraser", "09 Eraser.png"),
        }
        groups = (("pen",), ("highlighter", "horizontal_highlighter"), ("laser",), ("arrow",),
                  ("rectangle", "filled_rectangle"), ("circle", "filled_circle"), ("number", "letter"), ("eraser",))
        for i, names in enumerate(groups):
            name = names[0]
            label, filename = self.tool_specs[name]
            button = self.button(label, filename, lambda checked=False, key=name: self.set_tool(self.tool_buttons[key].tool))
            button.tool = name
            button.setCheckable(True)
            button.setChecked(name == self.tool)
            self.tools.addButton(button)
            for name in names:
                self.tool_buttons[name] = button
            if len(names) > 1:
                button.tool_menu = QMenu(button)
                button.tool_menu.setStyleSheet(
                    "QMenu { background: white; color: #454551; border: 1px solid #d8dce4; padding: 5px; }"
                    "QMenu::item { padding: 9px 20px 9px 8px; }"
                    "QMenu::item:selected { background: #eef0f4; border-radius: 6px; }")
                for name in names:
                    label, filename = self.tool_specs[name]
                    action = button.tool_menu.addAction(tool_icon(filename), label)
                    action.setCheckable(True)
                    action.setChecked(name == button.tool)
                    action.triggered.connect(lambda checked=False, tool=name: self.set_tool(tool))
                    self.tool_actions[name] = action
                button.setToolTip(button.toolTip() + "; right-click or use the arrow for more tools")
                button.setAccessibleDescription("More tools: right-click, dropdown arrow, or Alt+Down")
            grid.addWidget(button, i // 4, i % 4)
        tools_layout.addLayout(grid)
        row = QHBoxLayout()
        for label, filename, action in [
            ("Undo", "10 Undo.png", self.undo), ("Redo", "11 Redo.png", self.redo),
            ("Clear annotations", "12 Clear Annotations.png", self.clear),
            ("Move annotations", "13 Mouse Pointer.png", lambda: self.set_tool("move")),
            ("Interact with desktop", "13 Mouse Pointer.png", self.interact),
        ]:
            button = self.button(label, filename, action)
            if label == "Move annotations":
                button.setText("Move")
                button.setCheckable(True)
                self.tools.addButton(button)
                self.tool_buttons["move"] = button
            row.addWidget(button)
        tools_layout.addLayout(row)
        color_box = QGroupBox("Color")
        color_layout = QVBoxLayout(color_box)
        layout.addWidget(color_box)
        self.variant_control = QWidget()
        self.variant_control.setObjectName("segmentedChoices")
        row = QHBoxLayout(self.variant_control)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.variant = QButtonGroup(self)
        for i, name in enumerate(("Normal", "Pastel")):
            button = QPushButton(name)
            button.setCheckable(True)
            button.setObjectName("segmentChoice")
            self.variant.addButton(button, i)
            button.setChecked(i == 0)
            row.addWidget(button)
        self.variant.idClicked.connect(self.refresh_colors)
        color_layout.addWidget(self.variant_control)
        self.swatches = QButtonGroup(self)
        self.swatch_track = SwatchTrack(self.swatches)
        row = QHBoxLayout(self.swatch_track)
        row.setContentsMargins(4, 4, 4, 4)
        for i, name in enumerate(COLOR_NAMES):
            button = ColorSwatch()
            button.setToolTip(name)
            button.setAccessibleName(name)
            button.setCheckable(True)
            button.setChecked(i == 0)
            self.swatches.addButton(button, i)
            row.addWidget(button)
        self.swatches.idClicked.connect(self.set_color)
        color_layout.addWidget(self.swatch_track)
        self.refresh_colors()
        settings_box = QGroupBox("Size and Markers")
        settings_layout = QVBoxLayout(settings_box)
        layout.addWidget(settings_box)
        self.settings_row = QWidget()
        row = QGridLayout(self.settings_row)
        row.setContentsMargins(0, 0, 0, 0)
        self.pen_width = SlimSpinBox()
        self.highlighter_width = SlimSpinBox()
        self.shape_width = SlimSpinBox()
        for widget, value in ((self.pen_width, 4), (self.highlighter_width, 20), (self.shape_width, 4)):
            widget.setRange(1, 40)
            widget.setValue(value)
        self.size = SlimSpinBox()
        self.size.setRange(20, 120)
        self.size.setValue(40)
        self.laser_size = SlimSpinBox()
        self.laser_size.setRange(4, 80)
        self.laser_size.setValue(16)
        self.laser_size.setAccessibleName("Laser size")
        self.laser_size.setToolTip("Laser dot diameter in pixels")
        self.sequence = MarkerSequence()
        self.sequence.setRange(1, 999999)
        self.sequence_label = QLabel("Next")
        for index, (label, widget) in enumerate((("Pen width", self.pen_width),
                                                ("Highlighter width", self.highlighter_width),
                                                ("Marker size", self.size), ("Shape width", self.shape_width))):
            cell = QVBoxLayout()
            cell.setSpacing(0)
            caption = QLabel(label)
            if widget is self.size:
                self.marker_size_label = caption
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setAccessibleName(label)
            cell.addWidget(caption)
            cell.addWidget(widget, alignment=Qt.AlignmentFlag.AlignCenter)
            if widget is self.size:
                cell.addWidget(self.laser_size, alignment=Qt.AlignmentFlag.AlignCenter)
            row.addLayout(cell, index // 2, index % 2)
        row.setColumnStretch(0, 1)
        row.setColumnStretch(1, 1)
        row.setVerticalSpacing(8)
        self.sequence_divider = QWidget()
        self.sequence_divider.setFixedHeight(13)
        divider_layout = QHBoxLayout(self.sequence_divider)
        divider_layout.setContentsMargins(0, 6, 0, 6)
        divider_layout.setSpacing(0)
        divider_layout.addStretch(1)
        divider_line = QWidget()
        divider_line.setFixedHeight(1)
        divider_line.setStyleSheet("background: #cdd2dc; border: none;")
        divider_layout.addWidget(divider_line, 4)
        divider_layout.addStretch(1)
        row.addWidget(self.sequence_divider, 2, 0, 1, 2)
        extra = QHBoxLayout()
        extra.addStretch()
        extra.addWidget(self.sequence_label)
        extra.addWidget(self.sequence)
        extra.addStretch()
        row.addLayout(extra, 3, 0, 1, 2)
        settings_layout.addWidget(self.settings_row)
        # Reserve the marker controls' row so tools and tabs share one stable size.
        for widget in (self.sequence, self.sequence_label, self.sequence_divider):
            policy = widget.sizePolicy()
            policy.setRetainSizeWhenHidden(True)
            widget.setSizePolicy(policy)
        self.update_settings()
        capture_box = QGroupBox("Capture")
        capture_layout = QVBoxLayout(capture_box)
        layout.addWidget(capture_box)
        self.capture_control = QWidget()
        self.capture_control.setObjectName("segmentedChoices")
        row = QHBoxLayout(self.capture_control)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.capture_scope = QButtonGroup(self)
        self.had_selection = False
        for i, name in enumerate(("Spotlight area", "Full monitor")):
            button = QPushButton(name)
            button.setCheckable(True)
            button.setObjectName("segmentChoice")
            self.capture_scope.addButton(button, i)
            button.setChecked(i == 1)
            button.setEnabled(i == 1)
            row.addWidget(button)
        capture_layout.addWidget(self.capture_control)
        row = QHBoxLayout()
        self.capture_button = self.button("Capture screen", "15 Capture Screen.png", self.capture)
        row.addWidget(self.capture_button)
        self.copy_button = self.button("Capture and copy", "16 Copy to Clipboard.png", self.capture_and_copy)
        self.save_button = self.button("Save PNG", "17 Save Image.png", self.save)
        self.save_button.setEnabled(False)
        row.addWidget(self.copy_button)
        row.addWidget(self.save_button)
        capture_layout.addLayout(row)
        for section_layout in (tools_layout, color_layout, settings_layout, capture_layout):
            section_layout.setContentsMargins(14, 6, 14, 8)
        self.status = QLabel("")
        self.status.setWordWrap(True)

    def button(self, label, filename, action):
        button = IconButton()
        if label in ("Capture screen", "Capture and copy", "Save PNG"):
            button.setText({"Capture screen": "Capture", "Capture and copy": "Capture && Copy", "Save PNG": "Save PNG"}[label])
        else:
            button.setIcon(tool_icon(filename))
        button.setIconSize(QSize(27, 27))
        button.setFixedHeight(38)
        button.setMinimumWidth(52)
        button.setToolTip(TOOL_DESCRIPTIONS.get(label, label))
        button.setAccessibleName(label)
        button.clicked.connect(action)

        return button

    def set_tool(self, tool):
        was_laser = self.tool == "laser"
        self.overlay.pending = None
        self.overlay.reset_edit()
        if self.tool in ("arrow", "rectangle", "circle"):
            self.tool_widths[self.tool] = self.shape_width.value()
        self.tool = tool
        if tool in ("arrow", "rectangle", "circle"):
            self.shape_width.setValue(self.tool_widths.get(tool, 4))
        button = self.tool_buttons[tool]
        button.tool = tool
        button.setChecked(True)
        label, filename = self.tool_specs[tool]
        button.setIcon(tool_icon(filename))
        button.setAccessibleName(label)
        button.setToolTip(TOOL_DESCRIPTIONS[label] + (
            "; right-click or use the arrow for more tools" if button.tool_menu else ""))
        if button.tool_menu:
            for action in button.tool_menu.actions():
                action.setChecked(action is self.tool_actions[tool])
        self.overlay.setCursor(Qt.CursorShape.ArrowCursor if tool == "move" else Qt.CursorShape.CrossCursor)
        self.update_settings()
        self.start()
        if was_laser != (tool == "laser"):
            self.overlay.present(True)
            self.controller.panel.raise_()

    @property
    def width(self):
        return {"pen": self.pen_width, "highlighter": self.highlighter_width,
                "horizontal_highlighter": self.highlighter_width}.get(self.tool, self.shape_width)

    def update_settings(self):
        laser = self.tool == "laser"
        # Hide the outgoing control first: showing both even briefly raises the
        # top-level window's minimum height, which Qt does not shrink afterward.
        (self.size if laser else self.laser_size).hide()
        (self.laser_size if laser else self.size).show()
        self.marker_size_label.setText("Laser size" if laser else "Marker size")
        marker = self.tool in ("number", "letter")
        for widget in (self.sequence, self.sequence_label, self.sequence_divider):
            widget.setVisible(marker)
        self.sequence_label.setText("Next letter" if self.tool == "letter" else "Next number")
        self.sequence.set_letters(self.tool == "letter")
        self.sequence.setToolTip(marker_label(self.sequence.value(), self.tool == "letter"))

    def sync_capture_scope(self):
        selected = not self.controller.focus.isEmpty()
        self.capture_scope.button(0).setEnabled(selected)
        if selected and not self.had_selection:
            self.capture_scope.button(0).setChecked(True)
        elif not selected:
            self.capture_scope.button(1).setChecked(True)
        self.had_selection = selected

    def set_color(self, index):
        self.color = index

    def refresh_colors(self, *_):
        for i, button in enumerate(self.swatches.buttons()):
            button.set_color(PALETTES[self.variant.checkedId()][i])

    def remember(self):
        self.history.append((list(self.marks), self.sequence.value()))
        self.history = self.history[-100:]
        self.future.clear()

    def undo(self):
        self.overlay.pending = None
        self.overlay.reset_edit()
        if self.history:
            self.future.append((list(self.marks), self.sequence.value()))
            self.marks, value = self.history.pop()
            self.sequence.setValue(value)
            self.overlay.update()

    def redo(self):
        self.overlay.pending = None
        self.overlay.reset_edit()
        if self.future:
            self.history.append((list(self.marks), self.sequence.value()))
            self.marks, value = self.future.pop()
            self.sequence.setValue(value)
            self.overlay.update()

    def clear(self):
        self.overlay.pending = None
        self.overlay.reset_edit()
        if self.marks:
            self.remember()
            self.marks = []
        self.sequence.setValue(1)
        self.overlay.update()

    def reset_screen(self):
        self.drawing = False
        self.overlay.pending = None
        self.overlay.reset_edit()
        self.overlay.hide()
        if self.controller.mode == "off":
            self.controller.disarm_escape()
        self.marks.clear()
        self.history.clear()
        self.future.clear()
        self.sequence.setValue(1)
        self.screen = None
        self.status.setText("")

    def start(self):
        c = self.controller
        target = c.selected_screen or c.panel.screen()
        if self.drawing and self.screen == target:
            self.status.setText(f"{self.tool_specs[self.tool][0]} active")
            return
        if self.screen and self.screen != target:
            self.reset_screen()
        self.screen = target
        if not c.focus.isEmpty():
            if c.mode != "present":
                c.activate("present", keep_controls=True)
        elif c.mode != "off":
            c.clear()
        c.panel.information.hide()
        self.drawing = True
        c.arm_escape()
        c.panel.showNormal()
        self.overlay.present(True)
        c.panel.raise_()
        self.overlay.sync_controls_mask()
        self.status.setText(f"{self.tool_specs[self.tool][0]} active")

    def interact(self):
        self.drawing = False
        if self.screen:
            self.overlay.present(False)
            self.controller.panel.raise_()
        if self.controller.mode == "off":
            self.controller.disarm_escape()
        self.status.setText("Desktop interaction")

    def capture_and_copy(self):
        self.capture(copy_to_clipboard=True)

    def capture(self, copy_to_clipboard=False):
        if self.capturing:
            return
        self.capturing = True
        self.capture_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        c = self.controller
        self.sync_capture_scope()
        if not c.focus.isEmpty():
            if c.mode != "present":
                c.activate("present", keep_controls=True)
        elif c.mode != "off":
            c.clear()
        self.interact()
        screen = c.selected_screen or self.screen or c.panel.screen()
        crop = QRectF(c.focus) if self.capture_scope.checkedId() == 0 and not c.focus.isEmpty() else QRectF(screen.geometry())
        c.panel.information.hide()
        c.panel.hide()
        self.status.setText("Capturing...")
        # Let the compositor remove our controls before reading desktop pixels.
        QTimer.singleShot(250, lambda: self.finish_capture(screen, crop, copy_to_clipboard))

    def finish_capture(self, screen, crop, copy_to_clipboard=False):
        try:
            if screen not in self.controller.app.screens():
                raise RuntimeError("The selected monitor is no longer available.")
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                raise RuntimeError("Screen capture is unavailable.")
            local = crop.translated(-QPointF(screen.geometry().topLeft()))
            ratio = pixmap.devicePixelRatio()
            physical = QRect(round(local.x() * ratio), round(local.y() * ratio),
                             round(local.width() * ratio), round(local.height() * ratio))
            captured = pixmap.copy(physical.intersected(pixmap.rect()))
            if captured.isNull():
                raise RuntimeError("The capture area is outside the selected monitor.")
            self.captured = captured
            if copy_to_clipboard:
                self.copy()
            else:
                self.status.setText(f"Captured {self.captured.width()} x {self.captured.height()} pixels")
        except Exception as error:
            self.status.setText(str(error))
        finally:
            self.capturing = False
            self.capture_button.setEnabled(True)
            self.copy_button.setEnabled(True)
            self.save_button.setEnabled(not self.captured.isNull())
            self.controller.show_panel()

    def copy(self):
        if not self.captured.isNull():
            QApplication.clipboard().setPixmap(self.captured)
            self.status.setText("Copied to clipboard")

    def save(self):
        if self.captured.isNull():
            return
        self.interact()
        path, _ = QFileDialog.getSaveFileName(self, "Save capture", "Screen Spotlight.png", "PNG image (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.status.setText("Image saved" if self.captured.save(path, "PNG") else "Could not save image")
