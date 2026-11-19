# Landing keyboard focus implementation

User's complete requested interaction: initial focus on Spotlight/Annotation; one Tab goes to Select area. Existing controls remain reachable and tab change/drawing behavior stays intact. Small specified change; use existing Qt focus system, no broader UI redesign.

- [x] Add failing initial-focus/Tab/Shift+Tab/Space regressions and visible tab-focus rendering test in tests/test_spotlight.py. Capture RED.
- [x] At the end of Panel construction establish explicit tabBar -> Select area order and initial tabBar focus. Retain the existing visible focus indicator in custom SlidingTabBar paint (characterization check already passed before changes). Keep initial-only focus assignment so restoring controls does not reset a user's chosen focus. Run focused GREEN, verify remaining controls remain reachable.
- [x] Bump0.1.41, synchronize version/docs, regenerate runner and rebuild EXE using existing spec. Update artifact probe with initial-focus/one-Tab assertions and verify EXE+runner. Run affected spotlight tests, retain unrelated prior evidence.
- [x] Fresh read-only review. Sync guarded files and tested binary to C:/tools/myblib/screenspotlight, preserve installer work and README section, build matching installer and ZIP. Back up/update configured external runner. No commit, remote push or actual install/uninstall.

Working source is staged in the writable workspace; destination GitHub checkout receives guarded exact changes, same as prior sync. Existing0.1.40 source bytes match both copies before change. Version41 is this coherent keyboard behavior change. Verification scope is focus chain, actual Space activation, reverse traversal, visible focus and artifact startup; no unrelated AI/browser or full physical monitor run is needed.
