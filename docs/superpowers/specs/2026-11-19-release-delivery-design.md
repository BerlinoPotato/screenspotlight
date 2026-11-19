# Release delivery and ABC text icon

Approved scope: restore the already-approved feature delivery and create the requested ABC Text icon. User requests implementation; no additional design choice is required.

Evidence: canonical 0.1.39 source, embedded PLAR runner and standalone archive contain Text, monitor selector and global mode switch. The configured PLAR script in obeetwo/msrc is an independent self-contained 0.1.31 copy. Screenshot matches older UI but its exact 0.1.39 process is no longer running, so that specific artifact cannot be identified with certainty. Do not claim the stale 0.1.31 runner explains the screenshot's version label.

Implementation: add transparent ABC PNG in the existing icon style; use it on Text before and after activation. Synchronize version0.1.40, source, generated PLAR runner and canonical portable exe. Back up and replace only the configured deployed PLAR runner; preserve PLAR configuration/category and other projects. Confirm deployment hash. Do not terminate unknown user processes.

Verification: RED/GREEN Text icon regression and runtime artifact probe (execute actual bundled classes offscreen, check Text icon, horizontal drag, monitor selector, mode switch, capture outside both scroll tabs, wheel safety). Probe regenerated runner and new exe. Run affected annotation/improvement/PLAR tests, package startup/portable check and visually inspect real executable if app access permits. Preserve old evidence and actual failures.
