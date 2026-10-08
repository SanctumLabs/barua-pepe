> **Status: Proposed. Discovery output dated 2026-10-07; not accepted architecture.** Describes the code as inspected on that date and a proposal for its replacement. Decisions are tracked in the ADR index and open-question log.

# barua-pepe: GitHub issues filed

Repository: SanctumLabs/barua-pepe. Filed 2026-10-07. Before filing I listed all issues (4, all closed: #841 to #844, the Oct 2026 contract, dispatch seam, delivery policy and SMTP envelope work) and pull requests (none open; closed ones are merged dependabot and feature PRs). None of the findings duplicates a closed issue. Nothing pre-existing was edited or commented on.

Children are attached to their epic as sub-issues. Labels per the brief: one `severity:*`, one `type:*`, one `area:*`, one `phase:*`. (The GitHub tool created new labels only for issues created without a parent, so children were created first and then attached.)

## Epics

| # | Title | Severity | Phase |
|---|---|---|---|
| 858 | Epic: Phase 0 - stop the bleeding (security defaults, mail correctness, CI, container) | P1 | 0 |
| 859 | Epic: Phase 1 - platform contract and delivery-state foundation | P1 | 1 |
| 860 | Epic: Phase 2 - provider plug-in model and send pipeline | P1 | 2 |
| 861 | Epic: Phase 3 - provider feedback, suppression and unsubscribe compliance | P1 | 3 |
| 862 | Epic: Phase 4 - security, multi-tenancy and sending reputation | P1 | 4 |
| 863 | Epic: Phase 5 - observability, scaling and operations | P2 | 5 |
| 864 | Epic: Phase 6 - test strategy, dependency health and tech debt | P2 | 6 |

## Child issues

| # | URL | Title | Sev | Epic | Findings |
|---|---|---|---|---|---|
| 865 | https://github.com/SanctumLabs/barua-pepe/issues/865 | Reject default API credentials and fix production-config detection (ENV vs ENVIRONMENT) | P1 | 858 | BAR-001, BAR-002 |
| 866 | https://github.com/SanctumLabs/barua-pepe/issues/866 | Replace the 5 s message TTL on the primary queues with per-message expiry via versioned queues | P1 | 858 | BAR-007 |
| 867 | https://github.com/SanctumLabs/barua-pepe/issues/867 | Fix SMTP MIME construction: attachments, HTML bodies, display names and partial recipient refusals | P1 | 858 | BAR-009, BAR-010, BAR-011 |
| 868 | https://github.com/SanctumLabs/barua-pepe/issues/868 | Fix SMTP session lifecycle: authenticate in the worker, enforce TLS, add network timeouts | P1 | 858 | BAR-012, BAR-013 |
| 869 | https://github.com/SanctumLabs/barua-pepe/issues/869 | Fix production JSON logging and application lifecycle hooks | P1 | 858 | BAR-019, BAR-020 |
| 870 | https://github.com/SanctumLabs/barua-pepe/issues/870 | Repair the Dockerfile and docker-compose: reproducible build, supported base images, worker entrypoint | P1 | 858 | BAR-033 |
| 871 | https://github.com/SanctumLabs/barua-pepe/issues/871 | Repair CI: make Lint pass, test the PR head, fix workflow triggers and supply-chain risks | P1 | 858 | BAR-034 |
| 872 | https://github.com/SanctumLabs/barua-pepe/issues/872 | Make enqueue non-blocking and return 503 with Retry-After when the broker or result backend is unavailable | P1 | 858 | BAR-016 |
| 873 | https://github.com/SanctumLabs/barua-pepe/issues/873 | Repair the dependency lock, patch advisories and move to a supported Python | P2 | 858 | BAR-035 |
| 874 | https://github.com/SanctumLabs/barua-pepe/issues/874 | Define and version the transport-agnostic send contract (command, state event, error taxonomy) | P1 | 859 | BAR-021 |
| 875 | https://github.com/SanctumLabs/barua-pepe/issues/875 | Add idempotent acceptance: required idempotency key, request hashing and replay semantics | P1 | 859 | BAR-008 |
| 876 | https://github.com/SanctumLabs/barua-pepe/issues/876 | Persist message state: PostgreSQL schema, migrations, delivery state machine and status API | P1 | 859 | BAR-022 |
| 877 | https://github.com/SanctumLabs/barua-pepe/issues/877 | Publish delivery-state events through a transactional outbox (broker topic, optional signed callback) | P1 | 859 | BAR-022, BAR-016 |
| 878 | https://github.com/SanctumLabs/barua-pepe/issues/878 | Add a native broker intake (AMQP consumer) so services can publish without Celery internals | P1 | 859 | BAR-023 |
| 879 | https://github.com/SanctumLabs/barua-pepe/issues/879 | Introduce a provider registry with per-provider config, secrets, health and circuit breaker | P2 | 860 | BAR-024 |
| 880 | https://github.com/SanctumLabs/barua-pepe/issues/880 | Improve throughput: batching, connection pooling, priority lanes and per-provider concurrency | P2 | 860 | BAR-031 |
| 881 | https://github.com/SanctumLabs/barua-pepe/issues/881 | Redesign failure handling: attempt journal, one error taxonomy, bounded retries and a replayable DLQ | P1 | 860 | BAR-014, BAR-015 |
| 882 | https://github.com/SanctumLabs/barua-pepe/issues/882 | Clean broker and result-backend configuration, decouple the worker from the API import, remove dead code | P2 | 860 | BAR-017, BAR-018 |
| 883 | https://github.com/SanctumLabs/barua-pepe/issues/883 | Decide and implement email templating, localisation and plain-text alternatives | P2 | 860 | BAR-028 |
| 884 | https://github.com/SanctumLabs/barua-pepe/issues/884 | Enforce an attachment policy: size and type limits, input validation, AV scanning and claim-check storage | P2 | 860 | BAR-004, BAR-030 |
| 885 | https://github.com/SanctumLabs/barua-pepe/issues/885 | Add a provider webhook receiver with signature verification, replay protection and state mapping | P1 | 861 | BAR-025 |
| 886 | https://github.com/SanctumLabs/barua-pepe/issues/886 | Add a per-tenant suppression list enforced before every send, with API and events | P1 | 861 | BAR-026 |
| 887 | https://github.com/SanctumLabs/barua-pepe/issues/887 | Implement unsubscribe support: List-Unsubscribe headers and RFC 8058 one-click | P2 | 861 | BAR-027 |
| 888 | https://github.com/SanctumLabs/barua-pepe/issues/888 | Replace shared Basic auth with service authentication, tenant model, scoped authz and verified sender domains | P1 | 862 | BAR-003 |
| 889 | https://github.com/SanctumLabs/barua-pepe/issues/889 | Remove PII and secrets from logs, results and events; protect /metrics, /docs and Flower | P2 | 862 | BAR-005, BAR-006 |
| 890 | https://github.com/SanctumLabs/barua-pepe/issues/890 | Add per-tenant and per-provider rate limits, quotas, warm-up schedules and a complaint circuit breaker | P2 | 862 | BAR-029 |
| 891 | https://github.com/SanctumLabs/barua-pepe/issues/891 | Make metrics and health checks truthful: worker metrics, readiness, exporter placement and tracing | P2 | 863 | BAR-032 |
| 892 | https://github.com/SanctumLabs/barua-pepe/issues/892 | Define SLOs, alerts, runbooks and queue-depth autoscaling, and rehearse failure modes | P2 | 863 | BAR-031, BAR-032 |
| 893 | https://github.com/SanctumLabs/barua-pepe/issues/893 | Build the test pyramid foundation: provider fakes, real-auth API tests, contract tests, Testcontainers and quality gates | P2 | 864 | BAR-037 |
| 894 | https://github.com/SanctumLabs/barua-pepe/issues/894 | Migrate Pydantic v1-style APIs and FastAPI startup hooks to current idioms | P3 | 864 | BAR-036 |
| 895 | https://github.com/SanctumLabs/barua-pepe/issues/895 | Fix documentation drift and remove stray files; add a LICENSE and an architecture and operations guide | P3 | 864 | BAR-038 |

| 897 | https://github.com/SanctumLabs/barua-pepe/issues/897 | Package barua-pepe as a self-contained, configuration-driven deployable unit | P2 | 863 | (D19) |
| 898 | https://github.com/SanctumLabs/barua-pepe/issues/898 | Provide GitLab CI and Bitbucket Pipelines for the mirrored repository from the same task entry points as GitHub Actions | P2 | 858 | (D16) |

Total: 40 issues (7 epics, 33 children). A stray tool call with a mistyped owner was rejected by the access check and created nothing.
