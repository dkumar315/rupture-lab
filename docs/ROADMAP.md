# Roadmap

RuptureLab v1.0 is feature-complete. The milestones below describe the path to the first public release.

## v1.0 — complete

- [x] FastAPI control API and deterministic demo target
- [x] transparent async reverse proxy
- [x] latency, HTTP error, timeout, and malformed-JSON fault injection
- [x] baseline → fault → recovery experiment engine
- [x] declarative resilience contracts
- [x] PostgreSQL persistence and Alembic migrations
- [x] Next.js experiment builder, history, and result views
- [x] live experiment metrics over reconnectable Server-Sent Events
- [x] production-style Docker Compose runtime and readiness checks
- [x] backend, frontend, browser, and full-stack system quality gates
- [x] v1.0 documentation and release packaging

## Possible future directions

These are intentionally not commitments for v1.0. They become useful only if the product scope grows.

- isolate proxy state per experiment to support safe parallel runs
- authenticated control-plane access for remote deployments
- exportable experiment reports
- configurable external targets and reusable experiment profiles
- longer-term observability for multi-instance deployments

The current architecture and its deliberate limits are documented in [architecture.md](architecture.md).
