# Screen Spotlight for PLAR

This is a self-contained Python edition generated from the current `spotlight.py`, `emergency.py`, and `screenspotlight.png`. It uses no ScreenSpotlight.exe. Version 0.1.18 includes the compact interface, information overlay, plain title and version footer, image icon, and automatic return to controls when an area is cleared or canceled.

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
