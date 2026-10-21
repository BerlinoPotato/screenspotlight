# Screen Spotlight for PLAR

This is a self-contained Python edition generated from `spotlight.py`, `annotations.py`, `emergency.py`, and the application and tool icons. It uses no ScreenSpotlight.exe. Version 0.1.37 stays synchronized with the portable single-executable Windows release. All light-gray section-card corner radii remain 12 logical pixels. Tabs and compact choices retain their existing radii. Controls remain available for editing, presentation, and annotation.

The annotation toolbar groups highlighter, rectangle, circle, and marker variants. Right-click a grouped button, click its dropdown arrow, or press Alt+Down while focused to choose by icon and name. Left-click reuses the group's last choice. The horizontal highlighter uses Shift for vertical strokes; rectangles use Shift for squares. Filled shapes use the selected palette color. The laser dot follows the mouse while hiding the normal cursor, which returns over the controls or when laser mode ends. The laser allows desktop clicks, uses the Color palette and its own Laser size value, and disappears on Esc, Pointer, or capture. The Capture card has exactly two actions: **Capture Image** takes a fresh screenshot and copies it to the clipboard; **Save Image** takes a fresh screenshot and opens a dialog to select its PNG name and location. Each works independently without a previous capture. Both are disabled during capture and while the save dialog is open. Canceling the dialog or a capture/save failure restores the controls; Save Image leaves the clipboard unchanged.

**Move** lets you drag any mark, or click one and use arrows (Shift for 10 pixels). A dashed box identifies the selection; each drag is one Undo step. Spotlight areas now survive unchanged display notifications, including while moving/resizing; actual geometry changes fit the area within its monitor. Removing unrelated monitors preserves the selected area.

Annotations stay pinned to their original monitor when controls or other applications move, tools or selections change, or a new spotlight is selected elsewhere. The Tools card identifies that monitor. Move the controls to a destination screen, then click **Move to this screen** and confirm to relocate the area without clearing marks, numbering, or Undo/Redo history. Cancel keeps the original screen. **Clear annotations** resets marks and numbering while keeping the screen pinned; Undo restores them. Display bounds and scaling changes preserve marks; offscreen marks remain saved. Disconnecting the pinned screen keeps its marks for the session and restores them in desktop-interaction mode when that identified screen reconnects. Full monitor capture uses the pinned annotation screen. Marks are not saved after quitting.

Spotlight and Annotation share one stable control-window size. Visible screen layers retain their native translucent backing surface while switching tabs or input modes, preventing the previous reset-related blink. Both Normal and Pastel have eight colors, with the same neutral black (`#212121`) as the last swatch.

## In PLAR

Select **Screen Spotlight** under **Utilities**, then **Run**. The regular Spotlight control window opens. It stays in Alt+Tab and the taskbar when minimized. Shape radio buttons, live dimming in edit mode, moving/resizing, and all shortcuts are preserved.

PLAR starts the script in a separate Python process, as it does for its other tools. This keeps Spotlight's Quit and emergency exit separate from PLAR. PLAR's Stop button can also terminate the Spotlight process.

The script uses PLAR's selected Python interpreter and requires `PySide6>=6.11.1,<7`. If missing, install `requirements.txt` into that interpreter. There is no package installation at launch. The existing per-user Spotlight settings and single-instance guard are shared with the standalone app, so quit the standalone before launching the PLAR edition.

In circle edit mode, drag anywhere along the circle edge to resize around its center, or drag inside to move. An invisible grab margin makes the edge easier to select, and the hover cursor shows the resize direction. No dots or rectangular outline are shown. Press Enter to lock.

Rectangle editing also uses invisible targets along every edge and corner. Hover to see the resize cursor, drag a side to resize one dimension, or drag a corner to resize both. Drag inside to move. No blue outline or dots are drawn.

Shape and dimming are remembered across restarts. Every launch starts Ready without dimming the screen or restoring an area. Previously saved areas are ignored.

Dimming uses a single radio row: **10, 20, 30, 50, 75, 85, 95, 100%**; + / minus steps through the presets. Only the selected monitor is dimmed; other monitors remain usable.

## Import manually or use on another computer

1. Copy `runner_screen_spotlight.py` to a permanent location, for example PLAR's `msrc` folder. This one file contains the spotlight and emergency-exit implementation.
2. Update `script` in `Screen Spotlight.tool.json` to that file's absolute path.
3. In PLAR use **Tools → Import Tool…**, choose the JSON file, and import it. This is a tool definition, not an Import Parameters file.
4. Choose **Screen Spotlight** and **Run**.

The runner template is `"{python}" -u "{script}"`; both paths are quoted to handle spaces. The inspected PLAR source resolves `{python}` to its own Python interpreter. If using a frozen PLAR executable whose command builder still uses `sys.executable`, configure the runner with an explicit installed Python interpreter instead of `{python}`. This does not require ScreenSpotlight.exe.

To register automatically in a known configuration:

```powershell
py plar/register_tool.py "C:\path\to\PLAR\msrc\tools_config.json"
```

Registration appends one entry and writes a timestamped backup. It refuses to overwrite a different existing entry. Reload PLAR's tools configuration after registration and before editing/saving tools in an already-open PLAR window.

## Verification

```powershell
py plar/runner_screen_spotlight.py --check
```

This checks Python imports without opening the UI. `snapshot.json` records the source and asset hashes used to prepare this edition. The PLAR runner embeds the emergency worker and icon so it remains a single-file tool.

After editing the application source or icon, run `py plar/prepare_runner.py` to update PLAR's runner. `build.cmd` also performs this step. Quit the running Spotlight process and launch it again from PLAR to load the changes; no tool reimport is needed when its script path is unchanged.
