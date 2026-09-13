# RuptureLab demo guide

This walkthrough demonstrates the complete v1.0 path in a few minutes: healthy traffic, a controlled failure, recovery, live metrics, contract evaluation, and durable history.

## Start the production-style stack

From the repository root, create the ignored Compose environment once:

```bash
password="$(openssl rand -hex 24)"
{
  printf 'RUPTURELAB_DB_PASSWORD=%s\n' "$password"
  printf 'RUPTURELAB_DATABASE_URL=postgresql+asyncpg://rupturelab:%s@postgres:5432/rupturelab\n' "$password"
} > .env
unset password
```

Then start the application:

```bash
docker compose up --build -d --wait
docker compose ps
```

All five services should report healthy. Open `http://localhost:3000`.

## Demo scenario

Create a new experiment with these values:

```text
Name: Product API recovery
Method: GET
Path: /demo/products
Requests per phase: 10
Interval between requests: 300 ms

Fault outcome: HTTP error
Injection probability: 100%
HTTP status: 503

Baseline minimum success rate: 100%
Minimum fault rate: 100%
Recovery minimum success rate: 100%
```

### What to show

1. **Overview** — point out persisted experiment history, contract pass rate, control API status, and the deliberately small architecture surface.
2. **Experiment builder** — show that request traffic, fault behavior, and recovery expectations are configured separately.
3. **Live run** — watch baseline requests succeed, the fault phase switch to HTTP 503s, and recovery return to success. The live request feed shows status, outcome, and measured latency as each request completes.
4. **Reconnect** — refresh the page once during the run. The SSE client reconnects and resumes from retained sequenced events rather than cancelling the experiment.
5. **Persisted result** — after completion, show the phase comparison, request-level trace, and individual contract checks.
6. **History** — return to the overview and show that the run is now part of durable PostgreSQL history.

## System proof

The release also includes a reproducible non-UI proof:

```bash
./scripts/system-smoke.sh
npm --prefix frontend run test:system
```

The smoke script verifies service health, non-root runtime users, concurrent-run rejection, experiment persistence, API restart recovery, proxy/target restart recovery, PostgreSQL rows, and named-volume persistence after the complete Compose stack is recreated.

The system Playwright test then drives a real Chromium browser through the containerized Next.js frontend, FastAPI control API, fault proxy, demo target, and PostgreSQL database.

## Useful interview explanation

A concise explanation of the design is:

> RuptureLab is a crash-test lab for APIs. It establishes a healthy baseline, applies one controlled proxy-level fault, clears it, measures recovery, and evaluates explicit resilience thresholds. The dashboard receives live progress over reconnectable SSE, while PostgreSQL stores the durable experiment graph. I kept fault injection in a separate transparent proxy so the target application does not need instrumentation or RuptureLab-specific code.

If asked about trade-offs, the most important ones are:

- one active experiment is intentional because one proxy instance has one mutable fault profile
- SSE is enough because progress is server-to-client and native reconnect semantics are useful
- live events stay bounded in memory while completed runs are durable in PostgreSQL
- the v1.0 Compose stack is hardened for local/test use, but the control plane is not presented as an authenticated multi-tenant production service
