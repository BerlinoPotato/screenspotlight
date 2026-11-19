# Visual monitor selection — 0.1.42

Use a compact popup from the existing annotation monitor selector. Draw clickable,
proportional rectangles using Qt screen positions, with numbered labels and full
names and logical resolutions below. Blue indicates the current target. Keep
existing confirmation and annotation continuity when selecting another screen.
Escape and outside clicks dismiss without changing the drawing session.

- [x] Add focused regression tests and confirm failure.
- [x] Implement popup, keyboard selection, hotplug refresh and safe dismissal.
- [x] Bump version, regenerate PLAR, run affected tests and package probes.
- [x] Review, build installer and synchronize GitHub checkout and deployed PLAR.

No native Windows display-ID mapping is introduced; numbering matches the existing
selector. Physical multi-monitor acceptance remains a user check. Protect existing
uncommitted installer work during explicit, hash-guarded file synchronization.
