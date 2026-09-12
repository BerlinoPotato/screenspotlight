"""Screen-space annotation tools and capture controls."""
from dataclasses import dataclass, field
from functools import lru_cache
from math import atan2, cos, sin, pi
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap, QRegion, QValidator
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QRadioButton, QSpinBox, QToolTip, QVBoxLayout, QWidget,
)


PALETTES = (
    ("#e53935", "#f58220", "#ffdc32", "#28b463", "#00bcd4", "#3265e8", "#d92caf"),
    ("#f5a6a3", "#ffc49a", "#fff0a3", "#a5dfb5", "#a0e4ec", "#afc4fa", "#efa9db"),
)
COLOR_NAMES = ("Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Magenta")


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


class MarkerSequence(QSpinBox):
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
        elif self.tool == "rectangle":
            path.addRect(rect)
        elif self.tool == "circle":
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

    def hit(self, point):
        path = self.path()
        stroke = QPainterPathStroker()
        stroke.setWidth(max(12, self.width))
        return stroke.createStroke(path).contains(point) or (bool(self.label) and path.contains(point))

    def paint(self, painter):
        painter.save()
        color = QColor(self.color)
        if self.tool == "highlighter":
            color.setAlpha(90)
        painter.setPen(QPen(color, self.width, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(color if self.label else Qt.BrushStyle.NoBrush)
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


class InkOverlay(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.pending = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Screen Spotlight annotations")

    def present(self, drawing):
        self.pending = None
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        if not drawing:
            flags |= Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not drawing)
        self.setGeometry(self.owner.screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.sync_controls_mask()
        self.show()
        self.raise_()
        if drawing:
            self.activateWindow()
            self.setFocus()

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
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1 if self.owner.drawing else 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        for mark in self.owner.marks:
            mark.paint(painter)
        if self.pending:
            self.pending.paint(painter)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.owner.drawing:
            return
        owner = self.owner
        point = event.position()
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
        if self.pending:
            point = event.position()
            point = QPointF(max(0, min(point.x(), self.width())), max(0, min(point.y(), self.height())))
            if self.pending.tool in ("pen", "highlighter"):
                self.pending.points.append(point)
            else:
                if self.pending.tool == "circle":
                    start = self.pending.points[0]
                    delta = point - start
                    side = min(abs(delta.x()), abs(delta.y()))
                    point = start + QPointF(side if delta.x() >= 0 else -side,
                                           side if delta.y() >= 0 else -side)
                self.pending.points = [self.pending.points[0], point]
            self.update()

    def mouseReleaseEvent(self, event):
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
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.owner.undo()
            elif event.key() == Qt.Key.Key_Y:
                self.owner.redo()


class IconButton(QPushButton):
    """Show hover help even while the separate drawing window owns focus."""
    def __init__(self):
        super().__init__()
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
        super().mousePressEvent(event)

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
        self.overlay = InkOverlay(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)
        tools_box = QGroupBox("Tools")
        tools_layout = QVBoxLayout(tools_box)
        layout.addWidget(tools_box)
        grid = QGridLayout()
        self.tools = QButtonGroup(self)
        self.tool_buttons = {}
        for i, (name, filename) in enumerate([
            ("pen", "02 Pen.png"), ("highlighter", "03 Highlighter.png"),
            ("arrow", "04 Arrow.png"), ("rectangle", "05 Rectangle.png"),
            ("circle", "06 Circle.png"), ("number", "07 Numbered Marker.png"),
            ("letter", "08 Lettered Marker.png"), ("eraser", "09 Eraser.png"),
        ]):
            button = self.button(name.title(), filename, lambda checked=False, tool=name: self.set_tool(tool))
            button.setCheckable(True)
            button.setChecked(name == self.tool)
            self.tools.addButton(button)
            self.tool_buttons[name] = button
            grid.addWidget(button, i // 4, i % 4)
        tools_layout.addLayout(grid)
        row = QHBoxLayout()
        for label, filename, action in [
            ("Undo", "10 Undo.png", self.undo), ("Redo", "11 Redo.png", self.redo),
            ("Clear annotations", "12 Clear Annotations.png", self.clear),
            ("Interact with desktop", "13 Mouse Pointer.png", self.interact),
        ]:
            row.addWidget(self.button(label, filename, action))
        tools_layout.addLayout(row)
        color_box = QGroupBox("Color")
        color_layout = QVBoxLayout(color_box)
        layout.addWidget(color_box)
        row = QHBoxLayout()
        self.variant = QButtonGroup(self)
        for i, name in enumerate(("Normal", "Pastel")):
            button = QRadioButton(name)
            self.variant.addButton(button, i)
            button.setChecked(i == 0)
            row.addWidget(button)
        row.addStretch()
        self.variant.idClicked.connect(self.refresh_colors)
        color_layout.addLayout(row)
        row = QHBoxLayout()
        self.swatches = QButtonGroup(self)
        for i, name in enumerate(COLOR_NAMES):
            button = QPushButton()
            button.setFixedSize(42, 36)
            button.setToolTip(name)
            button.setAccessibleName(name)
            button.setCheckable(True)
            button.setChecked(i == 0)
            self.swatches.addButton(button, i)
            row.addWidget(button)
        self.swatches.idClicked.connect(self.set_color)
        color_layout.addLayout(row)
        self.refresh_colors()
        settings_box = QGroupBox("Size and Markers")
        settings_layout = QVBoxLayout(settings_box)
        layout.addWidget(settings_box)
        self.settings_row = QWidget()
        row = QGridLayout(self.settings_row)
        row.setContentsMargins(0, 0, 0, 0)
        self.pen_width = QSpinBox()
        self.highlighter_width = QSpinBox()
        self.shape_width = QSpinBox()
        for widget, value in ((self.pen_width, 4), (self.highlighter_width, 20), (self.shape_width, 4)):
            widget.setRange(1, 40)
            widget.setValue(value)
        self.size = QSpinBox()
        self.size.setRange(20, 120)
        self.size.setValue(40)
        self.sequence = MarkerSequence()
        self.sequence.setRange(1, 999999)
        self.sequence_label = QLabel("Next")
        for column, (label, widget) in enumerate((("Pen width", self.pen_width), ("Highlighter width", self.highlighter_width), ("Marker size", self.size))):
            row.addWidget(QLabel(label), 0, column)
            row.addWidget(widget, 1, column)
            row.setColumnStretch(column, 1)
        extra = QHBoxLayout()
        extra.addWidget(QLabel("Shape width"))
        extra.addWidget(self.shape_width)
        extra.addStretch()
        extra.addWidget(self.sequence_label)
        extra.addWidget(self.sequence)
        row.addLayout(extra, 2, 0, 1, 3)
        self.settings_row.setMinimumHeight(76)
        settings_layout.addWidget(self.settings_row)
        self.update_settings()
        capture_box = QGroupBox("Capture")
        capture_layout = QVBoxLayout(capture_box)
        layout.addWidget(capture_box)
        row = QHBoxLayout()
        self.capture_scope = QButtonGroup(self)
        self.had_selection = False
        for i, name in enumerate(("Spotlight area", "Full monitor")):
            button = QRadioButton(name)
            self.capture_scope.addButton(button, i)
            button.setChecked(i == 1)
            button.setEnabled(i == 1)
            row.addWidget(button)
        row.addStretch()
        capture_layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(self.button("Capture screen", "15 Capture Screen.png", self.capture))
        self.copy_button = self.button("Copy to clipboard", "16 Copy to Clipboard.png", self.copy)
        self.save_button = self.button("Save PNG", "17 Save Image.png", self.save)
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        row.addWidget(self.copy_button)
        row.addWidget(self.save_button)
        capture_layout.addLayout(row)
        for section_layout in (tools_layout, color_layout, settings_layout, capture_layout):
            section_layout.setContentsMargins(8, 4, 8, 4)
        self.status = QLabel("")
        self.status.setWordWrap(True)

    def button(self, label, filename, action):
        button = IconButton()
        button.setIcon(tool_icon(filename))
        button.setIconSize(QSize(32, 32))
        button.setFixedHeight(48)
        button.setMinimumWidth(52)
        descriptions = {
            "Pen": "Pen: draw freehand strokes",
            "Highlighter": "Highlighter: draw translucent strokes",
            "Arrow": "Arrow: drag to point at something",
            "Rectangle": "Rectangle: drag to outline an area",
            "Circle": "Circle: drag to circle an area",
            "Number": "Numbered marker: click to place the next number",
            "Letter": "Lettered marker: click to place the next letter",
            "Eraser": "Eraser: click an annotation to remove it",
            "Undo": "Undo: reverse the last annotation change",
            "Redo": "Redo: restore the last undone change",
            "Clear annotations": "Clear annotations: erase all marks",
            "Interact with desktop": "Interact with desktop: stop drawing and use the app underneath; keep annotations visible",
            "Capture screen": "Capture: capture the chosen area with annotations",
            "Copy to clipboard": "Copy the latest capture to the clipboard (capture first)",
            "Save PNG": "Save the latest capture as a PNG image (capture first)",
        }
        button.setToolTip(descriptions.get(label, label))
        button.setAccessibleName(label)
        button.clicked.connect(action)
        button.setStyleSheet("QPushButton:checked { border: 2px solid #71d6ff; background: #364961; }")
        return button

    def set_tool(self, tool):
        if self.tool in ("arrow", "rectangle", "circle"):
            self.tool_widths[self.tool] = self.shape_width.value()
        self.tool = tool
        if tool in ("arrow", "rectangle", "circle"):
            self.shape_width.setValue(self.tool_widths.get(tool, 4))
        self.tool_buttons[tool].setChecked(True)
        self.update_settings()
        self.start()

    @property
    def width(self):
        return {"pen": self.pen_width, "highlighter": self.highlighter_width}.get(self.tool, self.shape_width)

    def update_settings(self):
        marker = self.tool in ("number", "letter")
        for widget in (self.sequence, self.sequence_label):
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
            button.setStyleSheet(f"QPushButton {{background: {PALETTES[self.variant.checkedId()][i]}; border: 2px solid #555; padding: 0;}} QPushButton:checked {{border: 4px solid white;}}")

    def remember(self):
        self.history.append((list(self.marks), self.sequence.value()))
        self.history = self.history[-100:]
        self.future.clear()

    def undo(self):
        self.overlay.pending = None
        if self.history:
            self.future.append((list(self.marks), self.sequence.value()))
            self.marks, value = self.history.pop()
            self.sequence.setValue(value)
            self.overlay.update()

    def redo(self):
        self.overlay.pending = None
        if self.future:
            self.history.append((list(self.marks), self.sequence.value()))
            self.marks, value = self.future.pop()
            self.sequence.setValue(value)
            self.overlay.update()

    def clear(self):
        self.overlay.pending = None
        if self.marks:
            self.remember()
            self.marks = []
        self.sequence.setValue(1)
        self.overlay.update()

    def reset_screen(self):
        self.drawing = False
        self.overlay.pending = None
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
            self.status.setText(f"{self.tool.title()} active")
            return
        if self.screen and self.screen != target:
            self.reset_screen()
        self.screen = target
        if not c.focus.isEmpty():
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
        self.status.setText(f"{self.tool.title()} active")

    def interact(self):
        self.drawing = False
        if self.screen:
            self.overlay.present(False)
            self.controller.panel.raise_()
        if self.controller.mode == "off":
            self.controller.disarm_escape()
        self.status.setText("Desktop interaction")

    def capture(self):
        c = self.controller
        self.sync_capture_scope()
        if not c.focus.isEmpty():
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
        QTimer.singleShot(250, lambda: self.finish_capture(screen, crop))

    def finish_capture(self, screen, crop):
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
            self.captured = pixmap.copy(physical.intersected(pixmap.rect()))
            self.copy_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.status.setText(f"Captured {self.captured.width()} x {self.captured.height()} pixels")
        except Exception as error:
            self.status.setText(str(error))
        finally:
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
