# Screen Spotlight 0.1.37

Version 0.1.37 simplifies capture to two buttons: **Capture Image** takes a fresh screenshot and copies it to the clipboard; **Save Image** takes a fresh screenshot and opens a dialog to choose where to save its PNG. Both actions work independently from the first click. Annotations remain pinned to their monitor, with **Move to this screen** available for confirmed relocation. The Windows application is packaged as one portable executable. The verified 0.1.37 build is `dist\ScreenSpotlight.exe` (also available in `dist\0.1.37\ScreenSpotlight.exe`). Copy it to any folder and run it without Python or an accompanying `_internal` folder. Dependencies unpack automatically into a temporary folder at startup, which can make launching slightly slower.

The desktop application displays pen width and highlighter width in the first row, with marker size and shape width in the second row. When the laser is selected, its separate size control replaces marker size; both values are retained during the session. Tooltips describe each action and remain available while the drawing overlay has focus. The Pointer button at the end of the action row stops drawing and lets clicks reach the underlying application without removing annotations. Pen defaults to 4 pixels and highlighter to 20 pixels; each retains its chosen width during the session.

A standalone Windows desktop tool built with Python and PySide6. Drag a rectangle or circle to keep part of your screen bright while dimming everything around it. Locked overlays stay on top and let mouse clicks reach your applications.

## Annotation and capture

Spotlight and Annotation share one control-window size and position. Switching tabs does not shrink, expand, or briefly hide the controls or visible screen layers. Space for marker settings and two status lines is reserved so tool changes also keep the footer steady.

The controls window has text-only Spotlight and Annotation pill tabs, with rounded Tools, Color, Size and Markers, and Capture cards. Click any drawing tool to start drawing immediately. The first drawing session pins the annotation area to the spotlight monitor (or the controls' monitor without a spotlight). Moving the controls or an underlying application, changing tools, selecting marks, switching tabs, and selecting a spotlight on another monitor keep annotations on that pinned screen. The controls remain visible, clickable, and movable, so you can switch tools directly; no separate start button is required. The drawing surface excludes the controls window. Drawing tools use matching textured image icons on rounded buttons with descriptive tooltips. The toolbar has eight buttons: pen, highlighter, laser, arrow, rectangle, circle, markers, and eraser. Highlighter, rectangle, circle, and marker buttons have a small dropdown arrow. Right-click the button, click its arrow, or focus it and press Alt+Down / Shift+F10 to open a menu showing each variation's icon and name. Left-click uses that group's last selected tool, and the button shows its icon. Each group remembers its selection for the session. The action row also has **Move**, alongside Undo, Redo, Clear annotations, and Pointer.

Choose one of eight colors and the Normal or Pastel segmented choice. **Black** is the last swatch in both palettes and uses the same neutral near-black, `#212121`, in each. Pen width, highlighter width, marker size, and shape width remain available together. The next sequence value appears for markers. Tools include pen, freehand and horizontal translucent highlighters, a laser pointer, arrows, outline and filled rectangles and circles, numbered markers, lettered markers, and an eraser that removes whole objects. The horizontal highlighter stays perfectly horizontal even when the mouse moves diagonally; hold Shift while dragging for a vertical line. Both highlighters share Highlighter width. Filled shapes use the selected Normal or Pastel color at full opacity; the eraser can remove them by clicking their interior. Hold Shift while drawing an outline or filled rectangle to make a square. Circles stay round.

Click **Move**, then drag any annotation to reposition it. Outline rectangles and circles can be grabbed from their interior; strokes and arrows can be grabbed along their ink. When marks overlap, the topmost mark is selected. A dashed box identifies the selected mark. You can also click a mark and use arrow keys to move by 1 pixel, or Shift+arrows for 10 pixels. Movement stays within the monitor and preserves the mark's size, shape, label, and color. Each drag is one undoable change. Click empty space to deselect, or choose a drawing tool to draw again. Esc or Pointer returns to desktop interaction.

The laser is a temporary glowing dot that follows the mouse on the annotation monitor. Its Laser size control ranges from 4 to 80 pixels, and it uses the current color palette. Only the dot is shown: the normal Windows cursor is hidden over the laser surface, including over underlying applications, while clicks still pass through. The normal cursor returns over the controls, outside its monitor, or when laser mode ends. Cursor visibility is restored on capture, quit, errors, and emergency exit; the cursor theme is unchanged. The laser creates no saved marks or undo entries. Esc, Pointer, switching tools/tabs, or starting a capture removes the dot.

Markers use the selected color; the next value sets or resets the sequence, with letters continuing from Z to AA.

Esc or Enter on the drawing surface ends drawing and restores click-through while keeping annotations. The pointer button also activates desktop interaction. Ctrl+Shift+P restores the controls without stopping drawing. Switching to the Spotlight tab ends drawing. Ctrl+Z and Ctrl+Y undo and redo on the drawing surface; the controls also provide undo, redo, and Clear annotations. One shared status shows the current activity or capture result. Spotlight clearing does not delete annotations. Marks stay at screen positions, do not follow scrolling, and are not restored after restart. The Tools card names the pinned screen. To relocate the area, move the controls to the destination monitor, click **Move to this screen**, and confirm. All marks, marker numbering, and Undo/Redo history retain their monitor-relative positions; Cancel keeps the original screen. **Clear annotations** resets marks and numbering while keeping the screen pinned, and Undo restores the cleared marks. Display position, resolution, and scaling changes preserve completed marks and history. Marks outside smaller screen bounds remain saved and reappear when those bounds expand or the area moves back. Disconnecting the pinned screen hides its surface and retains its marks for the session; reconnecting the same identified screen restores them in desktop-interaction mode, or use the confirmed move action to continue elsewhere. Marks are not saved across application restarts.

Capture uses Spotlight area / Full monitor segmented choices. Spotlight area is selected when an area first becomes available; without an area it is disabled and Full monitor is selected. Full monitor captures the pinned annotation monitor, even if the controls or spotlight are on another monitor. Spotlight area captures the spotlight's own monitor. A circular spotlight produces a square crop around the circle, preserving visible dimming in the corners. Captures include annotations and visible spotlight dimming but briefly hide and then restore the controls. The action row has exactly two buttons. **Capture Image** takes a fresh screenshot and copies it directly to the clipboard for pasting. **Save Image** takes a fresh screenshot and opens a save dialog to choose the PNG file name and location; it does not require a previous capture or change the clipboard. Each click on either action captures the current screen. Both buttons stay disabled during capture and while the save dialog is open. Canceling the save dialog returns to the controls. A failed capture opens no save dialog and keeps the clipboard unchanged; failed capture or file saving restores both buttons so you can retry. The temporary laser dot is excluded from captures. Capture depends on normal Windows desktop composition; protected content and exclusive fullscreen applications may not be captured.

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

The initial defaults are rectangle, 50% dimming, and no border in presentation. Dimming provides a continuous slider with a percentage readout and one row of preset buttons: **10, 20, 30, 50, 75, 85, 95, and 100% (solid black)**. The + / minus keys step through these presets. Editable and locked areas both use your chosen dimming, including 100% black. Only drawing a new area is capped at 75% so you can see where to select. You can stay in edit mode indefinitely and adjust dimming live. Shape and dimming are remembered in the current user's Windows settings (`HKEY_CURRENT_USER\Software\SpotHighlight\ScreenSpotlight`). Every launch starts Ready with no active area and no screen dimming. Previously saved areas are ignored. A circle is always round; switching from a rectangle uses the smaller dimension. In edit mode, drag anywhere along the circle edge to resize it around its center. The edge has an invisible grab margin and changes the hover cursor to show the resize direction; no dots or rectangular outline are shown. Drag inside to move, and press Enter to lock the area.

The control panel temporarily **minimizes** while drawing a new spotlight selection, then returns immediately when the area is selected. It stays visible during editing, presentation, and annotation, and the overlays exclude its bounds so the controls remain clickable. It remains in the taskbar and **Alt+Tab**; restore it with Alt+Tab or **Ctrl+Shift+P**. Outlines and resize handles are invisible while editing. Hover near any edge to see the resize cursor; rectangle corners resize both dimensions, while sides resize one dimension. **Minimize** keeps the app in the taskbar. Closing the control panel or choosing **Quit** exits and removes all overlays. Esc is registered globally while a spotlight or annotation drawing mode is active. Letter keys and +/minus are never captured globally. Hotkey conflicts are reported in the information overlay.

### Recovery and duplicate instances

The new build allows only one instance per user session using a lock in the user's temporary folder. Starting it again reports that it is already running instead of stacking another dimmer. **Quit all older builds before using this version**: older builds do not share the instance guard, and their dim layers and shortcuts can interfere.

Press **Esc** to clear. A backup Windows key-state check works even if the normal hotkey message is missed. If the interface stops responding, **hold Esc for 2 seconds**: a separate worker exits this process while a spotlight is active. This emergency exit may skip saving your most recent preferences. It removes this process's windows, not overlays belonging to an older copy.

Unfinished selection clears automatically after 60 seconds without interaction. Editable areas and presentation have no timeout. Unexpected Python UI errors clear the overlay and reopen the panel with an error message.

The app always starts with its controls visible. Legacy `--tray` arguments and `launch-tray.cmd` now open the controls normally. Clearing or canceling an area restores the controls on top. Instructions and shortcut details are available in the ⓘ information overlay.

## Monitors and limitations

Only the monitor containing the selection is dimmed. Other monitors have no active overlay and remain usable. Before a new drag starts, selection overlays temporarily cover all monitors so you can choose any monitor. A selection stays within the monitor where its drag starts; spanning multiple monitors is not supported. Display notifications preserve the spotlight when its monitor remains available. If that monitor moves or changes resolution, the area keeps its monitor-relative position where possible and is fitted within the new bounds. Circles remain round. Removing the selected monitor clears its spotlight safely; adding or removing unrelated monitors does not delete the selected area. Unchanged layout notifications during moving/resizing do not cancel the drag. Highlights stay at screen coordinates and do not track application windows. Selection and editing temporarily capture input; presentation restores click-through.

Designed for the normal Windows desktop. Secure desktops (such as UAC prompts), exclusive fullscreen applications, and screen-sharing software may handle overlays differently. Mixed-DPI physical monitor setups and screen sharing still need a manual check on your equipment. No administrator rights are normally required.

## Build a portable Windows application

```powershell
py -m pip install -r requirements-build.txt
py -m PyInstaller --noconfirm --clean ScreenSpotlight.spec
```

Or double-click `build.cmd`. Launch or distribute only `dist\ScreenSpotlight.exe`; the destination computer does not need Python or extra application files. The old `dist\ScreenSpotlight` folder, if present, belongs to previous builds. The executable is not code-signed. User preferences remain per-user rather than alongside the executable.

## Launch from PLAR

This repository contains the standalone helper; no PLAR source was provided to modify. Keep the QProcess on a persistent owner, and use absolute paths:

```python
from PySide6.QtCore import QProcess

# Packaged PLAR launching the packaged helper:
self.spotlight_process = QProcess(self)
self.spotlight_process.setProgram(str(tools_dir / "ScreenSpotlight.exe"))
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

Verification covers 80 automated tests, including spotlight geometry and input modes, annotation rendering, independently visible size controls, immediate drawing on tab entry, marker sequences and colors, letter entry, equal full-width tabs, undo/redo, erasing, Escape dispatch, monitor removal, capture cropping, persistent controls, capture radio availability, horizontal/vertical highlighter constraints, filled-shape rendering and interior erasing, Shift squares, grouped icon menus, laser input/lifecycle, fresh clipboard capture, capture failure recovery, moving all annotation types with immutable undo snapshots, keyboard nudging and bounds, cursor visibility/restoration, preserving spotlight areas during layout notifications and drags, shared window geometry across tabs/tools, black drawing in both palettes, pinned annotation areas across control/spotlight monitor changes, retained marks and history during display changes and disconnection/reconnection, confirmed screen relocation and cancellation, undoable Clear, capture of the pinned monitor, exactly two ready image actions, fresh PNG capture on every Save Image click, save cancellation, capture failure before saving, and file-write failure recovery. The Windows spotlight check verifies dragging through native Windows mouse messages without moving the real pointer. It also checks control-panel window flags, shortcut restoration, native click-through at 100% dimming, and hotkey dispatch/cleanup. The annotation Windows check verifies native hit testing, switching tools with visible controls, annotated capture pixels, exclusion of controls, crop size, panel layout, and real hover tooltips while drawing has focus, native grouped-menu selection, laser visibility/click-through and cursor restoration, moving marks, stable spotlight moving/resizing, constant panel geometry with no overlay hide events or native layered-surface drops during tab/tool switches, retained ink while moving the controls across the connected mixed-DPI monitors, confirmed relocation and cancellation, both black palettes, fresh clipboard content, and newly captured PNG pixels at the chosen save path; it restores the pointer and saves previews of both tabs. The package check copies only the executable into a temporary folder and checks startup/exit and rejection of a second instance there. Actual browser clicking/scrolling and physical mixed-DPI setups remain manual checks.

Manual check: select an area over a browser, click and scroll both inside and outside it, edit and resize, try the global shortcuts while the browser has focus, then clear and quit. Repeat on monitors with different scaling settings.

Implementation references: [Qt window flags and translucency](https://doc.qt.io/qt-6/qt.html), [Windows RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey), and [Windows cursor visibility](https://learn.microsoft.com/en-us/windows/win32/api/magnification/nf-magnification-magshowsystemcursor).

The title bar is exactly `Screen Spotlight`. Version `0.1.37` appears only at the bottom of the controls window. Increment the patch version with each change. The application, tray, and Windows executable icons use `screenspotlight.png` (with `screenspotlight.ico` for Windows packaging). Annotation drawing tools use the PNGs in `icons` (new icon prompts are recorded in [icons/README.md](icons/README.md)); tabs and capture actions use text labels. Version metadata is defined in `version_info.txt`.
