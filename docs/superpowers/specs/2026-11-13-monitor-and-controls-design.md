# Screen Spotlight: predictable monitors and accessible controls

Status: approved for direct implementation and visual user acceptance on 2026-11-13.

## Intent

Make annotations stay on the intended monitor and make frequent drawing, desktop interaction, and capture actions easy to reach. Address accidental size changes while scrolling and wasted panel space.

## Approaches

- Automatically follow the pointer: convenient for hotkeys, but clicking the controls makes the pointer identify the controls' monitor. Rejected because it can repeat the reported surprise.
- Explicit monitor selection: user-approved approach. Display the chosen monitor and retain it across tools, desktop interaction, tab changes, and controls movement.
- Floating toolbar: an alternative for frequent actions, but adds another window. Proposed choice is to improve the existing panel with fixed shared actions.

## Monitor behavior

Show an annotation monitor selector with recognizable screen names and numbered labels. Before the first drawing session, preselect the controls' monitor and visibly identify it; do not silently prefer the spotlight monitor. The user can choose another monitor before drawing.

After the first session, tool changes, controls movement, spotlight selection, and Draw / Interact toggling never reassign the annotation monitor. Choosing a different annotation monitor with saved marks requires confirmation; preserve monitor-local positions, numbering, and undo/redo history. Cancel keeps the previous monitor. Empty sessions may change monitors without confirmation.

Preserve existing disconnect/reconnect and display-layout handling: retain marks and history, avoid dereferencing a removed screen, and restore in desktop-interaction mode. Disconnected targets cannot begin drawing or capture. Do not automatically move their marks elsewhere.

The reported wrong-screen bug is not yet reproduced. Trace actual activation and display event paths and add regressions before claiming the cause is fixed. Include negative monitor origins, changed resolution, and different monitor targets in focused tests; report limits of physical mixed-DPI verification.

## Annotation features

- Add Text as a normal annotation tool. Click a position, enter multiline text in a small editor, and confirm or cancel. Empty/canceled input creates no mark or undo entry. Text uses the selected color and a separate font-size value. Committed text supports Move, Eraser, Clear, Undo/Redo, capture, and monitor relocation like other marks. Editing committed text is outside this change; undo or erase and replace it.
- Make Horizontal highlighter the default variant of the highlighter button. Keep freehand highlighter in its dropdown and retain session choices. The initial overall drawing tool remains Pen.
- Add a labeled Draw / Interact toggle outside scrolling content; retain the previous drawing tool and all marks. Clicking a drawing tool resumes drawing. Esc continues to restore desktop interaction.
- Proposed global shortcut: Ctrl+Shift+D toggles drawing and desktop interaction while the app runs. Preserve Ctrl+Alt+D as the existing local shortcut. Report registration conflicts and keep the on-screen toggle available. Ignore toggles while capture, text entry, or another modal dialog is active. Resuming through the global shortcut selects the Annotation tab and uses the chosen annotation monitor.

## Panel and capture

Use the existing PySide6 application. Initial client size is 480 x 800 (increased after native visual inspection to keep regular settings visible), minimum 360 x 480 logical pixels, clamped to available screen space. Keep resizing and scrolling for small displays. Switching tools or tabs must not resize or reposition the outer window.

Keep header, tabs, shared Draw / Interact toggle, capture controls, status, and footer outside scrolling content. Share one capture section across both tabs rather than duplicating state. Capture Image and Save Image must remain reachable without scrolling at the normal initial size.

Reduce card padding and redundant vertical spacing. Remove the reserved marker-settings row when unused; content may reflow inside its scrolling area without moving fixed actions. Keep controls legible, labeled, keyboard accessible, and usable at increased display scaling.

Wheel events over size, sequence, and other adjustable numeric fields must scroll the containing panel without changing values, including when a field has focus. Values change through typing, arrow keys, and explicit step buttons.

Capture has Spotlight area / Full monitor choices and shows its actual target. Spotlight area uses the spotlight's monitor; Full monitor uses the explicit annotation monitor, independent of active tab and controls position. With no spotlight, disable Spotlight area. Preserve existing clipboard, save dialog, overlay inclusion, laser exclusion, and recovery behavior. Disable capture and relevant mode changes during capture/save to prevent races.

## Constraints and delivery

Keep the title exactly Screen Spotlight and show version only in the controls footer. Deliver one coherent patch release, proposed 0.1.39, synchronizing source, version_info.txt, and current documentation. Regenerate the PLAR runner and rebuild using ScreenSpotlight.spec. This workspace currently has no Git repository; design commits are unavailable unless repository metadata is restored.

## Verification

Use red/green regressions for monitor selection and retention, wheel safety, text lifecycle/history and bounds, global-toggle state continuity, and shared capture targeting. Check panel reachability and tab stability at normal and small sizes. Run affected existing spotlight/annotation tests and package/PLAR checks appropriate to changed artifacts. Broaden if failures reveal shared risk. Perform available native interaction checks; clearly distinguish simulated monitor tests from physical mixed-DPI acceptance. Review the final implementation before delivery.

## Builder discretion

Exact spacing, compact control arrangement, text editor widget, text font-size limits, and selector labeling are implementation choices. Preserve existing icon style using code-native text presentation for Text if no suitable asset exists. No new dependencies, annotation persistence, cross-monitor drawing surfaces, or additional floating windows are intended.
