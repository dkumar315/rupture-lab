# Changelog

## 1.0.0 — 2026-09-13

First public release of RuptureLab.

### Core resilience workflow

- transparent reverse proxy with controlled latency, HTTP error, timeout, and malformed-JSON injection
- baseline → fault → recovery experiment orchestration
- request-level latency, status, transport-error, and injected-fault measurements
- phase summaries with success/failure counts, fault counts, average latency, and p95 latency
- declarative resilience contracts with persisted per-check outcomes
- local request-target validation that prevents experiment paths from replacing the configured proxy authority

### Live dashboard

- Next.js experiment builder and durable history
- live baseline/fault/recovery progress over Server-Sent Events
- sequenced event replay with `Last-Event-ID`
- request-level live feed and automatic transition to persisted results
- responsive desktop, tablet, and mobile interface with narrow-screen history and request-trace layouts
- distinct global and experiment-specific not-found states

### Persistence and runtime

- PostgreSQL experiment history with Alembic migrations
- production-style Docker Compose stack for frontend, API, fault proxy, demo target, and PostgreSQL
- dependency-aware health checks and readiness reporting
- non-root application containers, dropped capabilities, read-only backend filesystems, localhost-only published ports, and frontend security headers

### Quality gates

- 108 backend tests with 100% line and branch coverage
- 53 frontend unit/component tests with 100% statement, branch, function, and line coverage across project-owned frontend logic
- 5 browser UI flows
- real Compose-backed Chromium system test
- restart, persistence, concurrency, non-root, and recovery smoke checks
- Ruff, strict mypy, ESLint, Prettier, TypeScript, Alembic verification, pip-audit, and npm audit in CI
