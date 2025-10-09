# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Telemetry + Behavior Learning:
  - `/agent/metrics/ingest` endpoint for anonymous section analytics
  - `/agent/analyze/behavior` and `/agent/layout` for learned ordering
  - Frontend tracker + runtime layout reordering
  - `/agent/metrics/summary` for dashboard aggregation
  - `public/metrics.html` lightweight dashboard (no extra deps)
  - Nightly GitHub Action to auto-update `data/analytics/weights.json`
