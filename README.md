# Screen Spotlight 0.1.23

Version 0.1.23 displays pen width, highlighter width, and marker size side by side, with shape width beneath them. Icon tooltips describe each action and remain available while the drawing overlay has focus. The blue pointer below Eraser stops drawing and lets clicks reach the underlying application without removing annotations. Pen defaults to 4 pixels and highlighter to 20 pixels; each retains its chosen width during the session.

A standalone Windows desktop tool built with Python and PySide6. Drag a rectangle or circle to keep part of your screen bright while dimming everything around it. Locked overlays stay on top and let mouse clicks reach your applications.

## Annotation and capture

The controls window has large Spotlight and Annotation tabs, with bordered Tools, Color, Size and Markers, and Capture sections. Click any drawing tool to start drawing immediately on the spotlight monitor (or the controls' monitor without a spotlight). The controls remain visible, clickable, and movable, so you can switch tools directly; no separate start button is required. The drawing surface excludes the controls window. Tool icons are decoded and cached before display.

Choose one of seven colors and the Normal or Pastel radio option. Pen width, highlighter width, marker size, and shape width remain available together. The next sequence value appears for markers. Tools include pen, translucent highlighter, arrows, rectangles, circles, numbered markers, lettered markers, and an eraser that removes whole objects. Markers use the selected color; the next value sets or resets the sequence, with letters continuing from Z to AA.

Esc or Enter on the drawing surface ends drawing and restores click-through while keeping annotations. The pointer button also activates desktop interaction. Ctrl+Shift+P restores the controls without stopping drawing. Switching to the Spotlight tab ends drawing. Ctrl+Z and Ctrl+Y undo and redo on the drawing surface; the controls also provide undo, redo, and Clear annotations. One shared status shows the current activity or capture result. Spotlight clearing does not delete annotations. Marks stay at screen positions, do not follow scrolling, and are not restored after restart. Starting annotation on a different monitor or changing the display layout clears the previous monitor's marks.

Capture uses Spotlight area / Full monitor radio options. Spotlight area is selected when an area first becomes available; without an area it is disabled and Full monitor is selected. A circular spotlight produces a square crop around the circle, preserving visible dimming in the corners. Captures include annotations and visible spotlight dimming but briefly hide and then restore the controls. After Capture, use Copy to clipboard or Save PNG. Capture depends on normal Windows desktop composition; protected content and exclusive fullscreen applications may not be captured.

## Run the application

Python 3.10 or newer is required when running the source (built and tested here with Python 3.14 and PySide6 6.11.1).

```powershell
py -m pip install -r requirements.txt
py spotlight.py
```

Or double-click `launch.cmd` after installing the dependency.

1. Click **Select area**, then drag on the desired monitor. Release to keep the new area editable. Drag inside to move it, or drag anywhere along the shape edge or a rectangle corner to resize. Very small selections are ignored.
2. Press **Enter** to lock the area. You can then use your applications normally: the entire overlay is click-through in presentation mode.
3. Press **Ctrl+Shift+E** to edit. Drag inside the area to move it or drag anywhere along the shape edge or a rectangle corner to resize. Arrow keys move by 1 pixel; Shift+arrows move by 10. Press **Enter** or **Ctrl+Shift+E** again to return to presentation.
4. Press **Esc** or **Ctrl+Shift+X** to clear and restore the controls on top. Right-click also clears during selection or editing. Ordinary right-clicks during presentation go to your underlying application.
5. Press **Ctrl+Shift+F** anytime to draw a new area, replacing the existing one. Click the tray icon only when you want the controls.

| Control | Action |
| --- | --- |
| Ctrl+Shift+F | Select a new area, replacing the existing one |
| Ctrl+Shift+E | Toggle edit / presentation, or select if none exists |
| Alt+Tab / Ctrl+Shift+P | Return to the control panel |
| Esc / Ctrl+Shift+X | Clear and restore the control panel |
| Right-click | Clear while selecting or editing |
| Arrows / Shift+arrows | Move by 1 / 10 pixels while editing |
| R / C | Rectangle / circle, while selecting or editing |
| + / − | Adjust dimming, while selecting or editing |
| Enter | Lock a valid selection and allow clicks through |

The initial defaults are rectangle, 50% dimming, and no border in presentation. Dimming uses one row of radio presets: **10, 20, 30, 50, 75, 85, 95, and 100% (solid black)**. The + / minus keys step through these presets. Editable and locked areas both use your chosen dimming, including 100% black. Only drawing a new area is capped at 75% so you can see where to select. You can stay in edit mode indefinitely and adjust dimming live. Shape and dimming are remembered in the current user's Windows settings (`HKEY_CURRENT_USER\Software\SpotHighlight\ScreenSpotlight`). Every launch starts Ready with no active area and no screen dimming. Previously saved areas are ignored. A circle is always round; switching from a rectangle uses the smaller dimension. In edit mode, drag anywhere along the circle edge to resize it around its center. The edge has an invisible grab margin and changes the hover cursor to show the resize direction; no dots or rectangular outline are shown. Drag inside to move, and press Enter to lock the area.

The control panel temporarily **minimizes** while drawing a new spotlight selection, then returns immediately when the area is selected. It stays visible during editing, presentation, and annotation, and the overlays exclude its bounds so the controls remain clickable. It remains in the taskbar and **Alt+Tab**; restore it with Alt+Tab or **Ctrl+Shift+P**. Outlines and resize handles are invisible while editing. Hover near any edge to see the resize cursor; rectangle corners resize both dimensions, while sides resize one dimension. **Minimize** keeps the app in the taskbar. Closing the control panel or choosing **Quit** exits and removes all overlays. Esc is registered globally while a spotlight or annotation drawing mode is active. Letter keys and +/minus are never captured globally. Hotkey conflicts are reported in the information overlay.

### Recovery and duplicate instances

The new build allows only one instance per user session using a lock in the user's temporary folder. Starting it again reports that it is already running instead of stacking another dimmer. **Quit all older builds before using this version**: older builds do not share the instance guard, and their dim layers and shortcuts can interfere.

Press **Esc** to clear. A backup Windows key-state check works even if the normal hotkey message is missed. If the interface stops responding, **hold Esc for 2 seconds**: a separate worker exits this process while a spotlight is active. This emergency exit may skip saving your most recent preferences. It removes this process's windows, not overlays belonging to an older copy.

Unfinished selection clears automatically after 60 seconds without interaction. Editable areas and presentation have no timeout. Unexpected Python UI errors clear the overlay and reopen the panel with an error message.

The app always starts with its controls visible. Legacy `--tray` arguments and `launch-tray.cmd` now open the controls normally. Clearing or canceling an area restores the controls on top. Instructions and shortcut details are available in the ⓘ information overlay.

## Monitors and limitations

Only the monitor containing the selection is dimmed. Other monitors have no active overlay and remain usable. Before a new drag starts, selection overlays temporarily cover all monitors so you can choose any monitor. A selection stays within the monitor where its drag starts; spanning multiple monitors is not supported. Display layout/resolution changes clear the spotlight so it cannot become stranded. Highlights stay at screen coordinates and do not track application windows. Selection and editing temporarily capture input; presentation restores click-through.

Designed for the normal Windows desktop. Secure desktops (such as UAC prompts), exclusive fullscreen applications, and screen-sharing software may handle overlays differently. Mixed-DPI physical monitor setups and screen sharing still need a manual check on your equipment. No administrator rights are normally required.

## Build a portable Windows application

```powershell
py -m pip install -r requirements-build.txt
py -m PyInstaller --noconfirm --clean ScreenSpotlight.spec
```

Or double-click `build.cmd`. Launch `dist\ScreenSpotlight\ScreenSpotlight.exe`. Distribute the **entire ScreenSpotlight folder**, including `_internal`; the destination computer does not need Python. The executable is not code-signed. User preferences remain per-user rather than alongside the executable.

## Launch from PLAR

This repository contains the standalone helper; no PLAR source was provided to modify. Keep the QProcess on a persistent owner, and use absolute paths:

```python
from PySide6.QtCore import QProcess

# Packaged PLAR launching the packaged helper:
self.spotlight_process = QProcess(self)
self.spotlight_process.setProgram(str(tools_dir / "ScreenSpotlight" / "ScreenSpotlight.exe"))
self.spotlight_process.start()

# Source development alternative (python_exe must be a Python interpreter):
# self.spotlight_process.setProgram(str(python_exe))
# self.spotlight_process.setArguments([str(tools_dir / "screen_spotlight" / "spotlight.py")])
```

Do not use `sys.executable` as the Python interpreter from a frozen PLAR executable: it points to PLAR itself. The helper's tray **Quit** action closes the helper independently.

## Verification

```powershell
py -m unittest discover -s tests -v
```

Tests run with Qt's offscreen backend and cover drag selection, editing, circle geometry, screen bounds, state transitions, alpha rendering, and click-through window flags. They do not prove native click delivery to other Windows applications.

Additional Windows checks (these launch application windows and close them automatically):

```powershell
py tests/native_smoke.py
py tests/package_smoke.py
py tests/annotation_native_smoke.py
```

Verification covers 42 automated tests, including spotlight geometry and input modes, annotation rendering, independently visible size controls, immediate drawing on tab entry, marker sequences and colors, letter entry, equal full-width tabs, undo/redo, erasing, Escape dispatch, monitor removal, capture cropping, persistent controls, and capture radio availability. The Windows spotlight check moves the real mouse pointer temporarily to verify dragging, then restores it. It also checks control-panel window flags, shortcut restoration, native click-through at 100% dimming, and hotkey dispatch/cleanup. The annotation Windows check verifies native hit testing, switching tools with visible controls, annotated capture pixels, exclusion of controls, crop size, panel layout, and real hover tooltips while drawing has focus; it restores the pointer and saves previews of both tabs. The package check covers startup/exit and rejection of a second instance. Actual browser clicking/scrolling and physical mixed-DPI setups remain manual checks.

Manual check: select an area over a browser, click and scroll both inside and outside it, edit and resize, try the global shortcuts while the browser has focus, then clear and quit. Repeat on monitors with different scaling settings.

Implementation references: [Qt window flags and translucency](https://doc.qt.io/qt-6/qt.html), [Windows RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey).

The title bar is exactly `Screen Spotlight`. Version `0.1.23` appears only at the bottom of the controls window. Increment the patch version with each change. The application, tray, and Windows executable icons use `screenspotlight.png` (with `screenspotlight.ico` for Windows packaging). Annotation controls use the supplied PNGs in `icons`. Version metadata is defined in `version_info.txt`.
