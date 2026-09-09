# Development Roadmap

## 0. Foundation
- Repository setup
- FastAPI service
- Health endpoint
- Initial tests and linting

## 1. Demo target
- Deterministic sample API
- Read and write endpoints
- Behaviour suitable for resilience experiments

## 2. Reverse proxy
- Async HTTP forwarding
- Request and response metadata
- Transparent pass-through behaviour

## 3. Fault injection
- Latency
- HTTP error responses
- Timeouts
- Malformed responses
- Configurable probability and duration

## 4. Experiment engine
- Baseline phase
- Fault phase
- Recovery phase
- Repeatable experiment configuration

## 5. Resilience contracts
- Success-rate thresholds
- Latency thresholds
- Recovery-time thresholds
- Duplicate-write detection
- Pass/fail evaluation

## 6. Persistence
- PostgreSQL
- Experiment history
- Request metrics
- Database migrations

## 7. Dashboard
- Experiment configuration
- Live metrics
- Results
- History
- Failure visualisation

## 8. Engineering hardening
- Integration tests
- CI
- Docker Compose
- Structured logging
- Health checks

## 9. v1.0
- Demo mode
- Exportable report
- Architecture documentation
- Screenshots and demo recording
- Public GitHub release
