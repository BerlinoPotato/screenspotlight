# GitHub Desktop checkout synchronization

User explicitly requests syncing the completed changes into C:/tools/myblib/screenspotlight. Work in that specified checkout in place, preserve existing uncommitted installer work, and do not commit or push remotely. Deliver the existing0.1.40 release; no additional application behavior/version is introduced by copying it.

- [x] Preserve baseline/hash manifest of every overwritten file and hashes of installer/build/config files to protect.
- [x] Compare destination differences; preserve installer documentation and add current0.1.40 app source, icon, generated runner, regression tests, design/plan docs, and exact verified portable binary. Guard all existing file hashes before mutation.
- [x] Regenerate runner in destination; verify source/asset hashes and source/EXE/runner parity. Run destination focused tests and both artifact probes.
- [x] Preserve installer implementation and compile a matching0.1.40 setup using its existing Inno script and newly synced EXE (no install or uninstall of user apps).
- [x] Fresh read-only review of preservation and synchronization. Report local Git status and verification; leave staging/commit/push for user in GitHub Desktop.

Verification scope: same already-tested application is being copied, so use focused annotation/improvement/PLAR tests and built-artifact probes, binary hashes/version metadata, and installer compilation. No repeat of unrelated browser or physical monitor workflows. Existing installer install/uninstall acceptance is not rerun because installer logic is unchanged; label that limitation.
