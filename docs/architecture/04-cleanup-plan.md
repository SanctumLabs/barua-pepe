> **Status: Proposed. Discovery output dated 2026-10-07; not accepted architecture.** Describes the code as inspected on that date and a proposal for its replacement. Decisions are tracked in the ADR index and open-question log.

# barua-pepe: phased cleanup plan

Sizes: S (about 1-3 days), M (about 1-2 weeks), L (more than 2 weeks), for one engineer who knows the repo. Phases 0 to 6 map to GitHub epics (see `07-issues-filed.md`). Issue numbers refer to SanctumLabs/barua-pepe; the epics are #858 to #864 (phases 0 to 6).

Ordering logic: first remove the things that can hurt people or lose mail today (Phase 0), then lay down the contract and state that every later capability needs (Phase 1), then rebuild the pipeline on it (Phase 2), then add the feedback loop (Phase 3), then multi-tenant security and reputation (Phase 4), then operations (Phase 5). Test and dependency hygiene run alongside, with the CI and lock repairs first (Phase 0) and the rest last (Phase 6).

## Phase 0: stop the bleeding (size M, risk low to medium)
Goal: nothing in production can be abused or silently lose or corrupt mail, and the repo builds, lints and tests on every PR.

| Item | Findings | Size | Risk |
|---|---|---|---|
| Refuse default API credentials; fix `ENV`/`ENVIRONMENT` | BAR-001, 002 | S | low (breaking for deployments relying on defaults, so announce) |
| Replace the 5 s queue TTL with versioned queues, migrate | BAR-007 | M | medium (needs the README queue-migration procedure, run with consumers draining) |
| Fix SMTP MIME (attachments, HTML, names, partial refusal) | BAR-009, 010, 011 | M | medium (behaviour changes visible to recipients; needs fakes, see test strategy) |
| Fix SMTP session, auth, TLS, timeouts | BAR-012, 013 | S | low |
| Fix production logging, lifecycle, request id | BAR-019, 020 | S | low |
| Non-blocking enqueue, 503 on dependency failure | BAR-016 | S | low |
| Repair Dockerfile and compose | BAR-033 | S | low |
| Repair CI | BAR-034 | M | low |
| Repair lock, patch CVEs, move to a supported Python | BAR-035 | M | medium (3.10 to 3.12 jump, Celery/Pydantic upgrades) |

Dependencies: none between most items. CI repair should land first so that the other changes are gated. SMTP fixes need the provider fakes from Phase 6 (the first 10 tests list), so those tests are written together with the fixes.
Exit criteria:
- A fresh clone builds the Docker image and runs `make lint test` green in CI on a PR, from the PR head.
- No default credential is accepted when `ENV` or `ENVIRONMENT` is `production`, proven by a startup test.
- A message waiting 10 minutes in the main queue is still delivered (integration test).
- A two-attachment message sent through the SMTP adapter against a MailHog or `aiosmtpd` fake decodes byte-for-byte on the receiving side. HTML renders as HTML.
- Production-mode logs are valid JSON on stdout (test parses real output).
- With the broker down, the API answers `503` in under 2 s and `/readyz` fails.
- `pip-audit` clean in CI.

## Phase 1: platform contract and delivery-state foundation (size L, risk medium)
Goal: a caller can submit idempotently, get a `message_id`, and learn the outcome over REST or the broker.

| Item | Findings | Size |
|---|---|---|
| Specify and version the transport-agnostic contract (command, event, error taxonomy), publish JSON Schema/OpenAPI/AsyncAPI | BAR-021 | M |
| Idempotent acceptance | BAR-008 | M |
| PostgreSQL store, Alembic, state machine, status API | BAR-022 | L |
| Transactional outbox and outbound `EmailStateChanged` events | BAR-022, BAR-016 | M |
| Native inbound queue contract (AMQP consumer on the same application service) | BAR-023 | M |

Dependencies: needs Phase 0 CI and config. Answers to Q-BAR-04 (persistence, broker) and Q-BAR-05 (tenancy) first. Contract design needs agreement with niosys and ujumbe so both services share envelope fields.
Exit criteria: contract tests pass in both directions (REST and AMQP produce identical state sequences for the same input). Replaying the same `Idempotency-Key` ten times produces one send. Killing the API after commit and before publish loses nothing (chaos test). Every `accepted` message reaches a terminal state in a soak test, checked by a SQL query.

## Phase 2: provider plug-in model and send pipeline (size L, risk medium)
Goal: adding a provider is one adapter; retries and failures behave by a single documented taxonomy; attachments are safe.

| Item | Findings | Size |
|---|---|---|
| Provider registry, per-provider config and secrets, health, circuit breaker; remove or port Mailchimp | BAR-024 | M |
| Attempt journal, error taxonomy, retry with jitter, DLQ with replay, unknown-outcome handling | BAR-014, 015 | M |
| Attachment policy: limits, MIME validation, AV, claim-check storage | BAR-004, 030 | L |
| Broker and result-backend configuration cleanup, decouple worker from the API import, delete dead code | BAR-017, 018 | S |
| Throughput: batching, pooling, priority lanes, per-provider concurrency | BAR-031 | M |
| Templating decision and implementation (if the gateway renders) | BAR-028 | M |

Dependencies: Phase 1 state store and contract. ADR-1, ADR-3, ADR-5 and ADR-4 are decided at the start.
Exit criteria: shared provider contract-test suite passes for SMTP, SendGrid and one more adapter (or a fake registered through the same interface). No `mail_error_task` that drops data remains. Poison message replay demonstrated. A 25 MB attachment is rejected at intake. An EICAR attachment is blocked. Load test hits the capacity target without TTL loss.

## Phase 3: provider feedback, suppression and unsubscribe (size L, risk medium)
Goal: bounces, complaints and deliveries flow back into state, and the gateway stops mailing addresses it must not.

| Item | Findings | Size |
|---|---|---|
| Webhook receiver with signature verification, replay protection, mapping to states | BAR-025 | L |
| Suppression store and enforcement, with APIs and events | BAR-026 | M |
| Unsubscribe headers (List-Unsubscribe and RFC 8058 one-click) and the one-click endpoint or relay to niosys | BAR-027 | M |

Dependencies: Phase 1 (state and events), Phase 2 (attempt journal, provider ids). Q-BAR-03 (who owns suppression and preference) and Q-BAR-11 (marketing vs transactional).
Exit criteria: signed fixture webhooks (valid, expired, replayed, forged) produce the expected states. A hard-bounced address is never sent again (test). A one-click POST suppresses and emits an event. Headers pass a mail-tester or RFC 8058 validator.

## Phase 4: security, multi-tenancy and sending reputation (size L, risk medium to high)
Goal: only authorised services send as verified senders, within limits.

| Item | Findings | Size |
|---|---|---|
| Replace shared Basic auth with JWT/API keys, tenant model, scoped authz, sender-domain verification, SPF/DKIM/DMARC runbook | BAR-003 | L |
| PII and exposure hardening (logs, results, events, `/metrics`, `/docs`, Flower) | BAR-005, 006 | M |
| Per-tenant and per-provider rate limits, warm-up schedule, complaint circuit breaker | BAR-029 | M |

Dependencies: Phase 1 (tenant in contract), Q-BAR-05.
Exit criteria: negative authz test matrix passes (wrong tenant, wrong scope, unverified From, expired token). A tenant over quota gets 429 and does not affect another tenant (isolation test). No address, body or secret appears in logs, results or events (log-scan test with canary strings).

## Phase 5: observability, scaling and operations (size M, risk low)
| Item | Findings | Size |
|---|---|---|
| Correct metrics (worker vs API process), readiness, remove the exporter-in-API pattern, tracing | BAR-032 | M |
| SLOs, alerts, runbooks, autoscaling on queue depth, graceful shutdown, DR drill | BAR-032, 031 | M |

Exit criteria: dashboards show send, failure and unknown counts that match the database. A game-day (broker outage, provider outage, worker kill) meets the SLO targets in `03-target-design.md`.

## Phase 6: tests, dependencies and tech debt (size M, ongoing, risk low)
| Item | Findings | Size |
|---|---|---|
| Test pyramid foundation: provider fakes, contract tests, authn tests, Testcontainers integration, mutation gate | BAR-037 | L |
| Pydantic v1-API migration, FastAPI lifespan | BAR-036 | S |
| Docs cleanup, stray files, LICENSE decision, README rewrite | BAR-038 | S |

Phase 6 test work starts in Phase 0 (the first 10 tests) and grows with every phase. Only the later gates (mutation, soak) wait for the end.
Exit criteria: coverage and mutation gates in `05-test-strategy.md` enforced in CI. README matches the code (a docs test checks referenced paths and make targets exist).

## Critical path
CI repair (P0) to config fixes (P0) to contract and persistence (P1) to pipeline rewrite (P2) to webhooks and suppression (P3). Security (P4) can start in parallel with Phase 2 once the tenant field exists in the contract. The decisions that block the critical path are Q-BAR-01, 04, 05, 02 and 03.
