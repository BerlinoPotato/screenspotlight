# Screen Spotlight 0.1.40

Version 0.1.40 adds a colorful **ABC Text icon** and synchronizes the configured PLAR runner. It includes **Text annotations**, a deliberate **annotation monitor selector**, and fixed **Draw / Interact with desktop** and **Capture / Save** controls on both tabs. **Ctrl+Shift+D** switches drawing and desktop interaction globally. The highlighter button starts with **Horizontal highlighter**. Controls start at **480 x 800** logical pixels, fitted to available screen space, and resize down to **360 x 480**. Scrolling over numeric values and the monitor selector scrolls the panel without changing them.

The Windows application is packaged as one portable executable: `dist\ScreenSpotlight.exe` (release copy: `dist\0.1.40\ScreenSpotlight.exe`). Copy it to any folder and run it without Python or an accompanying `_internal` folder. Dependencies unpack into a temporary folder at startup. Choose the annotation monitor in Tools; changing tools, moving controls, or toggling desktop interaction never moves its marks.

Pen width and highlighter width appear together, with marker size and shape width below. Text or Laser size replaces marker size when that tool is selected; each value is retained for the session. Click a value to type, or use its arrow buttons. Pen defaults to 4 pixels and highlighter to 20 pixels. Unused marker-number rows collapse without resizing the outer window.

A standalone Windows desktop tool built with Python and PySide6. Drag a rectangle or circle to keep part of your screen bright while dimming everything around it. Locked overlays stay on top and let mouse clicks reach your applications.

The Windows installer is available as `dist\ScreenSpotlight-Setup-0.1.40.exe`; it retains the existing per-user installer, shortcuts, and uninstall support.

## Annotation and capture

Spotlight and Annotation retain your chosen window size and position. Both tabs scroll independently when needed. The labeled Draw / Interact switch, capture controls, status, and footer stay outside scrolling content. At the initial size on a sufficiently tall display, all regular annotation settings are visible. Tool and tab changes do not resize the window.

The controls have Spotlight and Annotation pill tabs and compact Tools, Color, and Size and Markers cards. Choose the annotation monitor in Tools; its initial selection is the controls' monitor, independently of any spotlight. Drawing tools include pen, highlighter, laser, arrow, rectangle, circle, markers, eraser, and **Text**. Highlighter, rectangle, circle, and marker buttons have dropdowns; right-click, click the arrow, or press Alt+Down / Shift+F10 to select a variant. Left-click uses the last chosen variant for that session. Undo, Redo, Clear, and Move sit below the drawing tools.

Choose one of eight colors and the Normal or Pastel segmented choice. **Black** is the last swatch in both palettes and uses the same neutral near-black, `#212121`, in each. Pen width, highlighter width, marker size, and shape width remain available together. The next sequence value appears for markers. Tools include pen, freehand and horizontal translucent highlighters, a laser pointer, arrows, outline and filled rectangles and circles, numbered markers, lettered markers, and an eraser that removes whole objects. The horizontal highlighter stays perfectly horizontal even when the mouse moves diagonally; hold Shift while dragging for a vertical line. Both highlighters share Highlighter width. Filled shapes use the selected Normal or Pastel color at full opacity; the eraser can remove them by clicking their interior. Hold Shift while drawing an outline or filled rectangle to make a square. Circles stay round.

**Text:** select Text (Ctrl+Alt+T), click a location, enter one or more lines, then confirm. Cancel or blank input adds nothing. Text uses the selected color and Text size (8-144 pixels); Move, Eraser, Clear, Undo/Redo, monitor relocation, and capture work normally. Long lines wrap to at most 480 pixels. Text near an edge is fitted within the screen; very tall text is reduced down to 8 pixels or rejected if it still cannot fit. To replace committed wording, erase or undo the mark and place new text.

Click **Move**, then drag any annotation to reposition it. Outline rectangles and circles can be grabbed from their interior; strokes and arrows can be grabbed along their ink. When marks overlap, the topmost mark is selected. A dashed box identifies the selected mark. You can also click a mark and use arrow keys to move by 1 pixel, or Shift+arrows for 10 pixels. Movement stays within the monitor and preserves the mark's size, shape, label, and color. Each drag is one undoable change. Click empty space to deselect, or choose a drawing tool to draw again. Esc or Interact returns to desktop interaction.

The laser is a temporary glowing dot that follows the mouse on the annotation monitor. Its Laser size control ranges from 4 to 80 pixels, and it uses the current color palette. Only the dot is shown: the normal Windows cursor is hidden over the laser surface, including over underlying applications, while clicks still pass through. The normal cursor returns over the controls, outside its monitor, or when laser mode ends. Cursor visibility is restored on capture, quit, errors, and emergency exit; the cursor theme is unchanged. The laser creates no saved marks or undo entries. Esc, Interact, switching tools/tabs, or starting a capture removes the dot.

Markers use the selected color; the next value sets or resets the sequence, with letters continuing from Z to AA.

Click any size or marker field to type a value and press Enter (or move focus) to apply it. Widths accept 1-40 pixels, marker size 20-120, laser size 4-80, and the next number 1-999999. Next letter accepts letters such as A, Z, or AA. The arrow buttons still step the value.

| Annotation shortcut (app active, Annotation tab) | Action |
| --- | --- |
| Ctrl+Alt+P / H / L / A | Pen / highlighter / laser / arrow |
| Ctrl+Alt+R / C / N / E | Rectangle / circle / numbered marker / eraser |
| Ctrl+Alt+M / D | Move annotations / toggle desktop interaction |
| Ctrl+Alt+T | Text |
| Ctrl+Shift+D (global) | Toggle drawing / desktop interaction |
| Add Shift to Ctrl+Alt+H / R / C / N | Horizontal highlighter / filled rectangle / filled circle / lettered marker |

Hover over a button or open a grouped tool menu to see its shortcut. Spotlight tooltips also show the existing global shortcuts, such as **Select area = Ctrl+Shift+F**.

Esc or Enter on the drawing surface ends drawing while keeping annotations. Click **Draw**, any drawing tool, or press **Ctrl+Shift+D** to resume the previous tool on the same monitor. **Interact with desktop** lets clicks and typing reach your apps. Ctrl+Shift+P restores the controls. Switching to Spotlight ends drawing. Ctrl+Z / Ctrl+Y undo and redo. Marks stay at monitor positions and do not follow application scrolling or survive restarting the app.

Choose another monitor in Tools to relocate annotations. Saved marks or history require confirmation; Cancel keeps the original target. Monitor-local positions, marker numbering, and Undo/Redo history are retained. Empty sessions can change target immediately. Clear annotations is undoable and retains the target. Display changes preserve marks and history, including marks beyond reduced bounds. Disconnecting the target hides its surface and retains marks; reconnecting restores them in desktop-interaction mode, or choose another monitor to continue.

Capture is shared by both tabs, names its actual monitor in the card heading, and uses Spotlight area / Full monitor choices. Spotlight area is selected when an area first becomes available; without an area it is disabled and Full monitor is selected. Full monitor captures the pinned annotation monitor, even if the controls or spotlight are on another monitor. Spotlight area captures the spotlight's own monitor. A circular spotlight produces a square crop around the circle, preserving visible dimming in the corners. Captures include annotations and visible spotlight dimming but briefly hide and then restore the controls. The action row has exactly two buttons. **Capture Image** takes a fresh screenshot and copies it directly to the clipboard for pasting. **Save Image** takes a fresh screenshot and opens a save dialog to choose the PNG file name and location; it does not require a previous capture or change the clipboard. Each click on either action captures the current screen. Both buttons stay disabled during capture and while the save dialog is open. Canceling the save dialog returns to the controls. A failed capture opens no save dialog and keeps the clipboard unchanged; failed capture or file saving restores both buttons so you can retry. The temporary laser dot is excluded from captures. Capture depends on normal Windows desktop composition; protected content and exclusive fullscreen applications may not be captured.

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

The initial defaults are rectangle, 50% dimming, and no border in presentation. Dimming provides a continuous slider with a percentage readout and two compact rows of preset buttons: **10, 20, 30, 50, 75, 85, 95, and 100% (solid black)**. The + / minus keys step through these presets. Editable and locked areas both use your chosen dimming, including 100% black. Only drawing a new area is capped at 75% so you can see where to select. You can stay in edit mode indefinitely and adjust dimming live. Shape and dimming are remembered in the current user's Windows settings (`HKEY_CURRENT_USER\Software\SpotHighlight\ScreenSpotlight`). Every launch starts Ready with no active area and no screen dimming. Previously saved areas are ignored. A circle is always round; switching from a rectangle uses the smaller dimension. In edit mode, drag anywhere along the circle edge to resize it around its center. The edge has an invisible grab margin and changes the hover cursor to show the resize direction; no dots or rectangular outline are shown. Drag inside to move, and press Enter to lock the area.

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

## Install on Windows

Run `dist\ScreenSpotlight-Setup-0.1.40.exe` on Windows 10 or 11 (x64). The default destination is `%LOCALAPPDATA%\Programs\Screen Spotlight`. The wizard lets you change the destination and add an optional desktop shortcut. Launch from the Start menu after setup, or select **Launch Screen Spotlight** on the final page. Remove it through **Settings > Apps > Installed apps > Screen Spotlight > Uninstall**. Per-user application preferences are retained when uninstalling. The installer and portable application are currently unsigned.

To build the installer, install the Python build dependencies above and [Inno Setup 6.3 or newer](https://jrsoftware.org/isdl.php), then run:

```powershell
py installer/build_installer.py
# Or supply a compiler path:
py installer/build_installer.py --iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

`build-installer.cmd` runs the same build. The script regenerates the PLAR runner, rebuilds `dist\ScreenSpotlight.exe` using `ScreenSpotlight.spec`, and packages that executable. The installer reads the executable's version metadata and refuses to build if it differs from `APP_VERSION` in `spotlight.py`. A stable application ID lets subsequent releases update the same installation.

To verify a newly built installer in an interactive Windows session:

```powershell
py tests/installer_smoke.py
```

This temporarily installs into a workspace test folder, checks Start menu and optional desktop shortcuts, launches the installed app, repeats setup, and checks uninstall cleanup. It refuses to run over an existing installation or Start menu shortcut and removes its temporary install and shortcuts afterward. Logs remain in `build`. Close running Screen Spotlight instances before testing.

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

For 0.1.40, `tests/artifact_ui_probe.py` exercises the actual built EXE code and bundled icons, plus the generated runner: Text commit and ABC icon, horizontal highlighter default, target selector, mode continuity, and shared controls on both tabs. This prevents a startup/version-only check from standing in for feature delivery. Evidence: `.superpowers/sdd/2026-11-19-release-delivery/`.

```powershell
py -m unittest discover -s tests -v
```

Tests run with Qt's offscreen backend and cover drag selection, editing, circle geometry, screen bounds, state transitions, alpha rendering, and click-through window flags. They do not prove native click delivery to other Windows applications.

Additional Windows checks (these launch application windows and close them automatically):

```powershell
py tests/native_smoke.py
py tests/package_smoke.py
py tests/annotation_native_smoke.py
py tests/controls_native_smoke.py
py tests/improvements_native_smoke.py
```

Historical 0.1.38 verification: 84 automated tests covered existing spotlight geometry/input modes, annotation rendering/history, capture/save recovery, display changes, and pinned-screen continuity. Original evidence logs are retained. Current 0.1.39 evidence is recorded separately in `.superpowers/sdd/2026-11-13-monitor-and-controls/`; see `verification.md` for the final commands and results. New regressions exercise explicit monitor selection, scroll safety, text lifecycle and rendering, fixed action reachability, global mode state continuity, and modal hotkey guards. Native checks exercise actual monitor selection on the connected mixed-DPI screens and inspect the native overlay target, text entry, fixed actions, and hotkey registration/dispatch. Browser interaction and screen-sharing behavior still need user acceptance on the working desktop.

Manual check: select an area over a browser, click and scroll both inside and outside it, edit and resize, try the global shortcuts while the browser has focus, then clear and quit. Repeat on monitors with different scaling settings.

Implementation references: [Qt window flags and translucency](https://doc.qt.io/qt-6/qt.html), [Windows RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey), and [Windows cursor visibility](https://learn.microsoft.com/en-us/windows/win32/api/magnification/nf-magnification-magshowsystemcursor).

The title bar is exactly `Screen Spotlight`. Version `0.1.40` appears only at the bottom of the controls window. Increment the patch version with each change. The application, tray, and Windows executable icons use `screenspotlight.png` (with `screenspotlight.ico` for Windows packaging). Annotation drawing tools use the PNGs in `icons` (new icon prompts are recorded in [icons/README.md](icons/README.md)); tabs and capture actions use text labels. Version metadata is defined in `version_info.txt`.


PLAR deployment: the running launcher is configured to use `C:/tools/obt/projects/obeetwo/msrc/runner_screen_spotlight.py`. That is a separate self-contained copy; regenerating only the canonical runner does not update it. Version0.1.40 synchronizes this configured copy after backing it up, preserving launcher configuration and category. Always check the actual configured runner when distributing future changes.
