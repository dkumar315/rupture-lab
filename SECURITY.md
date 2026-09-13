# Security policy

## Supported version

Security fixes are maintained for the current `1.0.x` release line.

## Intended deployment model

RuptureLab is a local/test-environment resilience workbench. It is designed to inject failures into APIs that you own or are explicitly authorized to test.

The v1.0 control plane is **not** an internet-facing multi-tenant service. In particular, the fault proxy control namespace (`/_rupturelab/*`) has no authentication layer. The provided Compose configuration therefore publishes application ports on `127.0.0.1` only and keeps PostgreSQL internal to the Compose network.

Do not expose the control API or fault proxy directly to an untrusted network without adding an appropriate authentication, authorization, and network-isolation layer.

## Secrets

No real credentials should be committed to the repository.

- Root `.env` files are ignored by Git.
- `.env.example` contains names only, not usable secrets.
- The local quick start generates a random PostgreSQL credential.
- System CI generates an ephemeral database credential at runtime.
- Completed experiment specifications persist request headers and JSON bodies. Use synthetic values only; do not enter real authorization tokens, cookies, credentials, or sensitive payloads.

If a real secret is committed accidentally, revoke or rotate it first, remove it from source, and rewrite affected Git history before treating the incident as resolved.

## Reporting a vulnerability

Please do not publish an exploitable security issue as a public GitHub issue. Use GitHub's private vulnerability reporting feature for this repository when available.

Include enough information to reproduce the issue, the affected component, and the expected security impact. Reports involving systems you do not own or have authorization to test are out of scope.
