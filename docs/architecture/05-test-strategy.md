> **Status: Proposed. Discovery output dated 2026-10-07; not accepted architecture.** Describes the code as inspected on that date and a proposal for its replacement. Decisions are tracked in the ADR index and open-question log.

# barua-pepe: test strategy

## 1. Current test reality (measured 2026-10-07)

| Check | Result |
|---|---|
| `pytest --ignore=tests/integration` | 82 passed, 1 skipped, about 3 s. They only run after `pip install --no-deps` of the locked set, because `pip install -r` fails to resolve (BAR-035). |
| `pytest tests/integration` | 1 test, fails locally because it needs `docker compose up broker`. In CI it requires a hand-made RabbitMQ user (`rabbitmqctl add_user`) per job, which has been the subject of 10 commits touching the integration workflow or test (four of them `fix(ci)`). |
| Coverage (`pytest --cov=app`) | 82% total. Low spots: `auth_service` 58%, `config` 70% (production validator untested), `smtp_proxy` 62%, `mailchimp_email_service` 28% (dead code), `tasks/exceptions` 0%. |
| Lint | `pylint app` exit code 4 (CI red). Black not enforced (24 files differ). No type checker. No security scanner except CodeQL on `main`. |

Quality of what exists:
- Good: the domain and DTO validation tests, the delivery-policy tests (primary and fallback branches), the exporter tests (bounded state, retries) and the queue-argument pinning test. They are fast and deterministic.
- Weak: every provider test mocks `smtplib.SMTP` or the SendGrid client, so the real MIME output, SMTP dialogue and provider payloads are never checked. That is why BAR-009, 010, 011 (corrupt attachments, HTML as text, partial refusal) are untested. Authentication is replaced by a dependency override for every API test (`tests/__init__.py:22`). The production logger, config validation and Celery wiring are never exercised in production mode (BAR-002, BAR-019). The unit test for the Celery task patches the provider, so retry semantics are not tested against a real broker.
- Misleading: `tests/tasks/test_queues_dlx.py` asserts that the 5 s TTL stays (pins BAR-007 rather than testing behaviour). `tests/loadtest/http_load.py` uses the default credentials and sends the literal attachment content `"string"`, so it produces 400 or 500 responses.
- Absent: contract tests, webhook tests, idempotency tests, concurrency tests, property tests, chaos tests, a real SMTP fake, mutation testing, a test for graceful shutdown.

## 2. Target pyramid

| Layer | Share | Tooling | Purpose |
|---|---|---|---|
| Unit (pure) | about 60% | pytest, hypothesis | Domain validation, MIME builder, taxonomy mapping, state machine, backoff maths, suppression logic |
| Component (in-process with fakes) | about 20% | pytest, `aiosmtpd` (real SMTP server fake), `respx` or a local HTTP fake per provider, fakeredis | Provider adapters against protocol-faithful fakes, application services with an in-memory port set, FastAPI TestClient with real auth |
| Contract | about 8% | JSON Schema, schemathesis or Dredd for REST, AsyncAPI validators, consumer-driven pacts with niosys | REST/AMQP/gRPC parity, schema compatibility, error codes, event sequences |
| Integration | about 10% | Testcontainers (PostgreSQL, RabbitMQ, MinIO, ClamAV), MailHog or `aiosmtpd` container | Outbox, claims and leases, retry scheduler, DLQ replay, webhook receiver with signed fixtures |
| End-to-end, load, soak, chaos | about 2% | locust (already present), toxiproxy, `pumba` or a kill script | Capacity, back-pressure, broker or DB or provider outage, restart mid-send |

## 3. Contract tests
- **Inbound:** a single JSON Schema for `SendEmail` is the source of truth. The same fixtures (valid and invalid, golden) run against the REST edge, the AMQP consumer and the gRPC edge, asserting the same state sequence and error code. Include the legacy `sendmail` shim fixtures until it is removed.
- **Outbound:** `EmailStateChanged` schema tests plus ordering rules (`sequence` monotonic, no transition out of terminal states) validated by a state-machine property test.
- **Cross-service (consumer-driven):** niosys publishes the pact for the way it calls and the events it expects. barua-pepe verifies in CI. ujumbe shares the envelope test fixtures so both gateways stay structurally identical.
- **Provider adapter suite:** one reusable test class every `ProviderPort` implementation must pass: accepted, 4xx permanent, 429, 5xx, timeout before and after body sent, partial recipient refusal, large attachment, HTML plus text, non-ASCII names, header injection attempts. Each adapter provides a protocol-faithful fake (`aiosmtpd`, local HTTP server replaying recorded sandbox responses). Optionally one nightly job runs the same suite against provider sandboxes (SendGrid sandbox mode, SES simulator addresses).

## 4. Provider fakes and sandboxes
- SMTP: `aiosmtpd` with programmable behaviour per recipient (250, 4xx, 5xx, drop connection, slow `DATA`). Assert on received RFC 5322 messages by parsing them with `email` (headers, parts, decoded attachment bytes).
- HTTP providers: recorded fixtures and a local server; signed webhook fixtures generated with test keys (valid, wrong key, stale timestamp, replay).
- Never call real providers from PR CI. Sandbox runs are nightly and non-blocking.

## 5. Load, soak and chaos
- **Load (locust, existing file fixed):** 300 msg/s sustained for 30 min and 2 000 msg/s for 2 min against fakes. Assert: intake p99, zero lost (DB count equals accepted), oldest queued age, no TTL expiry.
- **Soak:** 24 h at 100 msg/s with random provider latency. Watch memory, connection count, DB bloat, outbox lag.
- **Chaos:** kill the API between commit and response; kill the worker between the provider call and the commit; stop RabbitMQ for 5 min; stop PostgreSQL for 1 min; blackhole one provider; skew the clock. Invariant checked after each: every accepted message is terminal, duplicates under 0.01%, and no message is in `sending` without a live lease.
- **Idempotency stress:** 1 000 parallel requests with the same key produce one message.

## 6. Quality gates
- Coverage: 90% line and 85% branch on `app/` (excluding generated code), measured on unit plus component tests, not integration. Ratchet upward and never down (diff coverage 95% on PRs).
- Mutation testing: `mutmut` or `cosmic-ray` on the domain, MIME builder, taxonomy and state machine. Gate at 80% score for those packages, run nightly and on PRs touching them.
- Static: `ruff` (lint plus format, replacing Black and pylint noise), `mypy --strict` on core packages, `bandit`, `pip-audit`, `semgrep` (PII logging and string-built headers), CodeQL on PRs, Hadolint for the Dockerfile, `actionlint` for workflows.
- Flake control: no `sleep` in tests (bounded polling helpers only), quarantine list with an owner and an expiry, retries not allowed to hide failures.

## 7. CI gates (per PR, from the PR head)
1. Lint, format check, type check, security scan (parallel).
2. Unit and component tests with coverage and diff-coverage gates.
3. Contract tests.
4. Integration tests with Testcontainers (no hand-created broker users).
5. Docker image build, Trivy scan, smoke test of `/readyz`.
6. Nightly: mutation, provider sandbox suite, soak (weekly), dependency audit with an automatic issue on a new advisory.
Merge to `develop` requires 1 to 5. Releases require the nightly suite green in the last 24 h.

## 8. Test data and fixtures standards
- Builders (`aMessage().withAttachments(2)`) rather than JSON blobs. Golden RFC 5322 files for MIME assertions.
- Use reserved domains (`example.org`, `.test`) only. No real addresses or secrets in fixtures. A pre-commit hook scans for secrets.
- Canary strings (for example `PII-CANARY-7f3a`) are inserted into subjects, bodies and addresses, and tests assert they never appear in logs, metrics, results or events.
- Deterministic time and IDs (`freezegun`, injectable clock and id generator). Every random test prints its seed.
- Database tests run in transactions or on a fresh schema per test class and use real migrations.

## 9. Concrete first ten tests (write these first, in this order)
1. **`test_smtp_multiple_attachments_roundtrip`**: an `aiosmtpd` fake receives a message with two attachments (PDF and PNG, base64 input). Parse it and assert both parts exist with the right content types, filenames and byte-identical decoded content. (Fails today: BAR-009.)
2. **`test_smtp_html_message_is_multipart_alternative`**: HTML plus text in the request gives a `multipart/alternative` with both parts. (Fails today: BAR-010.)
3. **`test_smtp_partial_refusal_is_reported`**: the fake refuses one of three recipients with 550, so the result lists the refused recipient and the message state is not "all sent". (Fails today: BAR-011.)
4. **`test_production_config_rejects_default_api_credentials`**: with `ENV=production` and again with `ENVIRONMENT=production`, startup raises unless `USERNAME` and `PASSWORD` are set to non-default values. (Fails today: BAR-001, 002.)
5. **`test_api_requires_real_auth`**: no dependency override. Missing, wrong and right credentials give 401, 401 and 202. Covers the real `get_current_auth`.
6. **`test_production_logger_emits_valid_json`**: configure the logger with `ENV=production`, log one record, capture stdout, `json.loads` each line, and assert there are no handler errors. (Fails today: BAR-019.)
7. **`test_queued_message_survives_backlog`** (integration, RabbitMQ container): publish one message, wait longer than the old TTL with no consumer, start a worker, and assert delivery to the SMTP fake and no dead-lettering. (Fails today: BAR-007.)
8. **`test_enqueue_failure_returns_503_quickly`**: with an unreachable broker, `POST` returns 503 with `Retry-After` in under 2 s, and a parallel `/healthz` request is not delayed. (Fails today: BAR-016.)
9. **`test_same_idempotency_key_sends_once`** (after Phase 1): 20 concurrent requests with one key give one message row, one provider call and 20 identical responses; a changed body returns 409.
10. **`test_unknown_outcome_is_never_resent`**: the provider fake accepts `DATA` and then drops the connection. The message goes to `outcome_unknown`, exactly one provider submission exists, and an event is emitted. Resolution through a delivered webhook moves it to `delivered`.

Also add early (cheap and high value): a CRLF-injection test on subject, filename and header allow-list (should be a 422 at intake, BAR-004), and a state-machine property test that no sequence of events leaves a terminal state.
