# Screen Spotlight maintenance

- Increment the patch version for every user-requested change, including UI and text changes. Keep `spotlight.py`, `version_info.txt`, and current-version documentation synchronized.
- The window title is exactly `Screen Spotlight`. Do not add a personal signature. Show the version only in the footer of the controls window.
- Regenerate the self-contained PLAR runner with `py plar/prepare_runner.py` after source or icon changes. PLAR launches this runner directly, so updating only the standalone source or executable is incomplete.
- Rebuild the standalone executable using `ScreenSpotlight.spec` for application changes.
