# Monitor and Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Implement the approved monitor and controls design for visual user acceptance.
**Architecture:** Keep PySide6 and the existing overlay/mark model. Add explicit target selection and text marks in annotations.py; host shared mode/capture controls in Panel outside tab scroll areas.
**Tech Stack:** Python, PySide6, unittest, PyInstaller.
**Spec:** docs/superpowers/specs/2026-11-13-monitor-and-controls-design.md

## Global Constraints
- Title exactly Screen Spotlight; version only in controls footer.
- Patch 0.1.39, synchronized documentation/resources, regenerated PLAR runner, rebuilt standalone.
- No new dependencies or floating toolbar.
- User explicitly requested direct implementation and visual review; proceed inline without another approval stop.
- No Git metadata: preserve local baseline copies and ledger instead of unavailable Git-dependent scripts/commits.

## Review Focus
- Negative-origin/disconnected targets must preserve marks and history.
- Modal text/capture operations must block global mode changes.
- Text with multiple lines, whitespace, and oversized input must have consistent paint/hit/move bounds.
- Small windows and display scaling must keep shared actions reachable.
- Capture must name and use the target independently of the visible tab.

### Task 1: Explicit monitor and safe numeric scrolling
Files: annotations.py, tests/test_annotations.py, tests/test_improvements.py.
Interfaces: AnnotationTools.screen_selector, choose_screen(index), sync_screen_controls(), existing bind_screen/start/capture.
- [x] Add failing regressions for first annotation ignoring spotlight target, deliberate selector change/cancel/history, wheel delivery without numeric mutation, and highlighter button starting horizontal.
- [x] Run `py -m unittest discover -s tests -p test_improvements.py -v`; confirm expected RED.
- [x] Implement selector and preserve identity/disconnect behavior; ignore wheel changes in SlimSpinBox and pass scrolling to parent; default highlight group to horizontal.
- [x] Run focused tests; expect PASS. Record evidence.

### Task 2: Text marks
Files: annotations.py, tests/test_improvements.py.
Interfaces: Mark.path/paint/hit/translated, AnnotationTools.add_text(point), text_size, text_entry_active.
- [x] Add failing tests for multiline paint/hit/bounds, commit/cancel, history/move/erase, and screen changes during entry.
- [x] Run focused tests; confirm expected RED.
- [x] Implement Text tool, modal multiline editor, independent font size, glyph rendering with rectangular selection/hit bounds; clamp placement and cancel on target removal.
- [x] Run focused and existing annotation tests; expect PASS after updating intentional UI contracts only.

### Task 3: Shared fixed controls and global switch
Files: spotlight.py, annotations.py, tests/test_spotlight.py, tests/test_improvements.py, native smoke scripts.
Interfaces: AnnotationTools.capture_box, mode_control, sync_tool_buttons, Spotlight.toggle_annotation_mode().
- [x] Add failing tests for fixed capture/toggle reachability across tabs/small windows, wheel scroll propagation, global toggle retaining target/tool/marks, and modal guards.
- [x] Run focused tests; confirm expected RED.
- [x] Place labeled mode toggle and shared capture outside scroll; compact settings without blank marker row; initial 460 x 680 clamped to screen. Add Ctrl+Shift+D native hotkey with conflict feedback.
- [x] Run spotlight and annotation tests and native layout checks; expect PASS. Render both tabs and inspect images.

### Task 4: Review, version and delivery
Files: README.md, plar/README.md, spotlight.py, version_info.txt, generated runner, executable, evidence ledger.
- [x] Review complete source using fresh reviewer; resolve important findings with RED/GREEN tests.
- [x] Bump 0.1.39 and update documentation to actual behavior.
- [x] Run `py plar/prepare_runner.py`, `py -m unittest discover -s tests -v`; expect all PASS.
- [x] Rebuild `py -m PyInstaller --noconfirm --clean ScreenSpotlight.spec`; expect success.
- [x] Run package smoke and appropriate native checks; record actual results and physical-monitor limitations.
- [x] Deliver executable and visual previews for user review.
