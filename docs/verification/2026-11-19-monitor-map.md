# Monitor map — 0.1.42 — 2026-11-19

Scope: annotation monitor popup, monitor target continuity, keyboard dismissal,
hotplug refresh and packaged delivery. Map uses Qt logical desktop geometry;
numbers retain the existing screen enumeration. Full names and resolutions remain
available below the proportional map, including mirrored/overlapping displays.

Red/green: four new map tests initially failed because set_monitors was absent;
all passed after implementation. Fresh review identified Qt-first Escape followed
by emergency polling stopping drawing; an added regression reproduced the failure.
Routing both paths through the controller Escape latch fixed it.

Fresh verification: `py -m unittest discover -s tests`: **113 passed**.
Includes layout with negative origins and mixed orientation, names/resolutions,
click selection, keyboard selection/dismissal, hotplug, cancellation preserving
marks and target, Escape order, existing text/highlighter/capture/focus/wheel and
PLAR generation behavior. Review reported no other important issues.

Final clean-workpath PyInstaller build passed. Both actual executable archive and generated PLAR runner passed artifact_ui_probe with expected version0.1.42, including visual map, prior tool behavior and keyboard focus. Fresh review rechecked the Escape fix with five tests passing and no important remaining findings.

The existing root executable was in use. It was renamed to ScreenSpotlight-0.1.41-running.exe without ending the user session; the newly built executable now occupies the normal path. Restart is required.
Physical multi-monitor UI acceptance has not been repeated for this release.

Delivery: GitHub checkout and configured external PLAR runner byte comparisons passed. Protected installer source hashes unchanged. Portable ZIP payload equals current EXE. Inno Setup0.1.42 compiled successfully (21.469s); installer execution was not run. No commit or remote push performed.

SHA256 dist/0.1.42/ScreenSpotlight.exe: dd5b946811cfaaf0b5d23b3cc3883fc61d56b6d66f4517216aaf0ee581b6bf03

SHA256 plar/runner_screen_spotlight.py: a9a2cd3cf6efe27aaa9cdfdf98bea25e85e8717cbce0e4edefb2718fa78f25dd
