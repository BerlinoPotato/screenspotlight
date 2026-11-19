# Release Delivery Implementation Plan

> Required skill: superpowers:executing-plans. User requests direct implementation.

Goal: deliver requested features on the real launch paths and add an ABC Text icon.
Spec: docs/superpowers/specs/2026-11-19-release-delivery-design.md
Architecture: existing Qt mark model and self-contained runner; no new dependency.

- [x] Task1: write failing icon-consumer test in tests/test_improvements.py; run RED; add generated icons/25 Text.png, wire Text icon including set_tool path, run GREEN.
- [x] Task2: add tests/artifact_ui_probe.py; run it against0.1.39 packaged code, expect missing icon failure. Probe actual archived modules and assets, not imports from source. Verify horizontal stroke, Text icon, shared controls, target selector and wheel safety.
- [x] Task3: version0.1.40 synchronized in source/metadata/current docs; regenerate PLAR; build with ScreenSpotlight.spec into fresh versioned folders; probe EXE and runner; package startup check. Focused annotation/improvement/PLAR tests.
- [x] Task4: fresh read-only review; resolve important findings with regressions. Back up configured external PLAR runner then deploy exact generated file using scoped escalation. Verify hash and --check. Inspect executable UI, capture preview, report actual findings/limits.

Review focus: deployed runner must match actual configured path; built-code probe must never silently import source annotations; Text icon survives selection; preserve external config and user marks; no claim that screenshot artifact was definitively identified.

No Git repository exists; local baseline and progress/evidence ledger replace unavailable Git scripts/commits.
