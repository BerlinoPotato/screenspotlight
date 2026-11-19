"""Exercise the actual release artifact's Qt classes, never source modules."""
import argparse
import marshal
import os
from pathlib import Path
import runpy
import sys
import tempfile
import types
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication


def load_release(path, assets):
    if path.suffix == '.py':
        return runpy.run_path(str(path), run_name='release_probe')
    from PyInstaller.archive.readers import CArchiveReader
    archive = CArchiveReader(str(path))
    pyz = archive.open_embedded_archive('PYZ.pyz')
    for name in archive.toc:
        relative = name.replace('\\', '/')
        if relative == 'screenspotlight.png' or (relative.startswith('icons/') and relative.endswith('.png')):
            destination = assets / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.extract(name))
    for name in ('emergency', 'annotations'):
        module = types.ModuleType(name)
        module.__file__ = str(assets / (name + '.py'))
        sys.modules[name] = module
        exec(pyz.extract(name), module.__dict__)
    namespace = {'__name__': 'release_probe', '__file__': str(assets / 'spotlight.py')}
    exec(marshal.loads(archive.extract('spotlight')), namespace)
    return namespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--expected-version', required=True)
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='spotlight-artifact-probe-') as directory:
        ns = load_release(args.artifact.resolve(), Path(directory))
        assert ns['APP_VERSION'] == args.expected_version
        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        controller = ns['Spotlight'](app, native_hotkeys=False, persist=False)
        a = controller.annotations
        try:
            controller.show_panel()
            controller.panel.tabs.setCurrentIndex(1)
            app.processEvents()
            assert a.screen_selector.isVisible(), 'Release is missing the explicit monitor selector'
            assert a.tool_buttons['text'].isVisible(), 'Release is missing Text'
            assert not a.tool_buttons['text'].icon().isNull(), 'Release is missing the ABC icon'
            a.tool_buttons['highlighter'].click()
            QTest.mousePress(a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
            QTest.mouseRelease(a.overlay, Qt.MouseButton.LeftButton, pos=QPoint(240, 180))
            assert a.marks[-1].tool == 'horizontal_highlighter'
            assert a.marks[-1].points == [QPointF(100, 100), QPointF(240, 100)]
            a.tool_buttons['text'].click()
            assert not a.tool_buttons['text'].icon().isNull(), 'Selecting Text lost the ABC icon'
            dialog_type = sys.modules['annotations'].QInputDialog if args.artifact.suffix == '.exe' else ns['QInputDialog']
            with patch.object(dialog_type, 'getMultiLineText', return_value=('ABC release check', True)):
                a.add_text(QPointF(100, 200))
            assert a.marks[-1].tool == 'text' and a.marks[-1].label == 'ABC release check'
            snapshot = list(a.marks)
            target = a.screen_key
            controller.toggle_annotation_mode()
            assert not a.drawing
            controller.toggle_annotation_mode()
            assert a.drawing and a.tool == 'text' and a.screen_key == target
            assert a.marks == snapshot, 'Mode toggle lost committed marks'
            for tab in (0, 1):
                controller.panel.tabs.setCurrentIndex(tab)
                app.processEvents()
                for widget in (a.capture_button, a.save_button, a.draw_button, a.desktop_button):
                    assert widget.isVisible() and not controller.panel.tabs.isAncestorOf(widget)
            controller.panel.tabs.setCurrentIndex(1)
            for field in (a.pen_width, a.highlighter_width, a.shape_width, a.text_size, a.sequence):
                field.setFocus()
                before = field.value()
                wheel = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(), QPoint(0, -120),
                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                    Qt.ScrollPhase.NoScrollPhase, False)
                app.sendEvent(field, wheel)
                assert field.value() == before, 'Release changes numeric values while scrolling'
            selector = a.screen_selector
            selector.addItem('Artifact probe alternative', ('probe-only', '', '', ''))
            before = selector.currentIndex()
            wheel = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(), QPoint(0, -120),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                Qt.ScrollPhase.NoScrollPhase, False)
            app.sendEvent(selector, wheel)
            assert selector.currentIndex() == before, 'Release switches monitors while scrolling'
            a.sync_screen_controls()
            if args.preview:
                args.preview.parent.mkdir(parents=True, exist_ok=True)
                assert controller.panel.grab().save(str(args.preview))
            print(f'PASS: {args.artifact.name} {args.expected_version}: ABC icon, Text commit, default horizontal stroke, monitor selector, global toggle continuity, fixed Capture/Save and Draw/Interact on both tabs, numeric and monitor wheel safety')
        finally:
            controller.shutdown()
            controller.panel.hide()


if __name__ == '__main__':
    main()
