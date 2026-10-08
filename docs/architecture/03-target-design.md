> **Status: Proposed. Discovery output dated 2026-10-07; not accepted architecture.** Describes the code as inspected on that date and a proposal for its replacement. Decisions are tracked in the ADR index and open-question log.
>
> **Superseded or added points (maintainer decisions, 2026-10-07; see niosys `docs/platform/18-decision-log.md`).**
> 1. **Unknown outcome (sections 3.1 `on_unknown_outcome`, 5.3, ADR on unknown outcome):** "never auto-resends, hold" was replaced in the body below as well (section 5.3, the state model, the `SendEmail` example and ADR 9). A missed message is worse than a duplicate: reconcile by lookup; if nothing can be confirmed by the deadline, **resend, capped and counted**. `on_unknown_outcome` defaults to `resend`. Issue #881 amended.
> 2. **Broker (sections 1, 2, ADR-1):** Kafka is the production broker. barua-pepe moves from RabbitMQ/Celery to a **broker port with Kafka as the first binding**; RabbitMQ remains a configurable binding; the AMQP, exchange, `x-death` and KEDA-on-RabbitMQ mechanics in the body are now described as the optional binding, with Kafka equivalents first. Issue #878 rescoped. "PostgreSQL and RabbitMQ" in Q-BAR-04 becomes "PostgreSQL and Kafka".
> 3. **BAR-001:** default credentials are dev/test only; severity P1 (#865).
> 4. **Deployability:** whether the self-contained-unit principle applies here is open (Q-PLAT-19).
> 5. **Optional validity bound (proposed, not final):** no new attempt after `expires_at`; resend-after-unknown only within validity; `expired` is terminal and alerted (comment on #881). This is also the intended meaning of the 5 s queue TTL if it was meant to drop stale mail (#866).

# barua-pepe: target design

Scope: the email gateway inside the notification platform (niosys decides who gets what, barua-pepe decides how an email leaves the building and tells the caller what happened). Sketches only; no product code was written. Assumptions are marked (A) and are listed as open questions in `06-open-questions.md`.

## 1. Principles
1. **Accepted means durable.** `202` is returned only after the request is persisted (state row plus outbox in one transaction). Every accepted message ends in exactly one terminal state, and a reconciliation job proves it.
2. **Transport-agnostic contract.** One logical command (`SendEmail`) and one logical event stream (`EmailStateChanged`), expressible as a Kafka message (the first binding), an AMQP message (the optional RabbitMQ binding), a REST body or a gRPC message. The broker or REST choice is deployment configuration, never a code dependency.
3. **At-least-once everywhere, effectively-once sends.** Duplicate input is absorbed by idempotency keys. Duplicate provider submissions are avoided by an attempt journal plus the explicit "outcome unknown" state, and are never retried blindly.
4. **Provider-neutral core, thin adapters.** The core knows `ProviderPort.submit(OutboundMessage) -> SubmitResult`. Everything else is an adapter.
5. **The gateway owns mail mechanics** (MIME, provider quirks, bounces, complaints, suppression, unsubscribe headers, reputation). It does not own user preferences, which belong to niosys (Q-BAR-03, Q-BAR-02).

## 2. Boundaries and components

```
            REST/gRPC                          Kafka (first binding; others pluggable)
  caller ─────────────►  ┌──────────────┐ ◄──────────────── caller
                         │ Intake API   │  authn/z, validation, idempotency, size limits
                         └──────┬───────┘  (stateless, scales on RPS)
                                │  tx: messages + outbox
                         ┌──────▼───────┐
                         │ PostgreSQL   │  messages, attempts, events, outbox, suppressions, tenants, senders
                         └──┬────────┬──┘
              outbox relay  │        │  state of record
            ┌───────────────▼┐      ┌▼───────────────┐
            │ Work queue     │      │ Event publisher│──► `email.state.v1` topic / webhook / SSE
            │ (per priority) │      │ (outbox relay) │
            └──────┬─────────┘      └────────────────┘
                   │
            ┌──────▼───────┐   ProviderPort    ┌───────────────────────┐
            │ Send worker  │ ────────────────► │ SMTP | SendGrid | SES │ ... registry
            │ policy, retry│                   └──────────┬────────────┘
            │ rate limit   │                              │ webhooks / DSN / feedback
            └──────────────┘                   ┌──────────▼────────────┐
                                               │ Webhook receiver      │ signature verify, dedupe,
                                               │ (separate deployable) │ map to state + suppression
                                               └───────────────────────┘
   Supporting: attachment store (S3-compatible, AV scan), template renderer (optional, ADR-4),
   reconciler (stuck/unknown messages), admin/replay CLI, metrics/trace exporters.
```

| Component | Responsibility | Notes |
|---|---|---|
| Intake API (FastAPI, async) | Authenticates, authorises the sender, validates, checks idempotency, stores, returns 202. `GET` status. | Today's `app/api` plus `app/application`, with Celery removed from the request path. |
| Intake consumer | Same pipeline fed from a broker queue (`email.send.v1`). | Shares the application service with the REST edge. |
| Message store | PostgreSQL (ADR-2). | Migrations via Alembic. |
| Outbox relay | Moves committed rows to the work queue and the event stream. | Removes dual-write loss. |
| Send worker | Claims a message, applies suppression, limits and policy, renders MIME, calls a provider, records the attempt. | Stateless; scales on queue depth. |
| Provider registry | Maps names to adapters, with config, health and a circuit breaker per provider. | Replaces `mailer.py:25-32`. |
| Webhook receiver | Verifies signatures, deduplicates, translates provider events into state transitions and suppressions. | Public ingress, separate deployment and credentials. |
| Reconciler | Finds messages stuck in `queued`/`sending`/`outcome_unknown` past their SLA, and `sent` messages with no provider feedback after the feedback window. | Republishes, resolves via provider lookup, resends (capped), fails them, or closes `sent` as `delivered_unconfirmed`. |
| Attachment service | Pre-signed upload, size and MIME enforcement, AV scan, claim-check reference. | ADR-5. |

Existing code that stays: the `domain/entities` model (reshaped), `application/email_dispatch` seam, `delivery_policy` (extended), the SendGrid and SMTP adapters (after fixes), the Prometheus exporter idea, the DLX integration test idea.

## 3. Contracts (logical, versioned)

### 3.1 Command: `SendEmail` (schema `email.send.v1`)
Envelope fields are the same on REST (headers and body), Kafka (headers and value; AMQP properties and body on the optional RabbitMQ binding) and gRPC (metadata and message).

| Field | Where | Rules |
|---|---|---|
| `idempotency_key` | header `Idempotency-Key` / Kafka header `idempotency-key` (AMQP `message_id` on RabbitMQ) | **Required.** 1-255 chars. Scope is `(tenant_id, key)`. Same key and same body hash gives the original response. Same key and different body gives `409 idempotency_conflict`. Retained 7 days (A). |
| `correlation_id` | header `X-Correlation-Id` / Kafka header `correlation-id` (AMQP `correlation_id` on RabbitMQ) | Optional, echoed on every event. Generated if absent. |
| `tenant_id` | derived from credentials (REST/gRPC); signed envelope claim or per-tenant topic ACL (Kafka) or vhost (RabbitMQ) | Never trusted from the body on REST. |
| `schema_version` | `application/vnd.baruapepe.send.v1+json` | Additive changes only inside a major version. |
| `reply_to` | optional Kafka `reply-to` header (AMQP `reply_to` on RabbitMQ) / callback URL id | Where state events go if the caller wants a dedicated route. Default: shared `email.state.v1` stream. |

Body:
```json
{
  "from": {"email": "no-reply@brand.example", "name": "Brand"},
  "to":  [{"email": "a@example.org", "name": "A"}],
  "cc":  [], "bcc": [],
  "reply_to": {"email": "support@brand.example"},
  "subject": "Your receipt",
  "content": {"text": "…", "html": "<p>…</p>"},
  "template": {"id": "receipt", "version": "3", "locale": "sw-KE", "data": {"order": "A1"}},
  "attachments": [{"ref": "att_01J…", "filename": "receipt.pdf", "content_type": "application/pdf"}],
  "headers": {"X-Order-Id": "A1"},
  "category": "transactional",
  "unsubscribe": {"url": "https://…", "mailto": "unsub@brand.example", "one_click": true},
  "priority": "high",
  "send_after": "2026-10-08T07:00:00Z",
  "expires_at": "2026-10-08T07:15:00Z",
  "provider_hint": "primary",
  "on_unknown_outcome": "resend"
}
```
Rules: exactly one of `content` or `template`. `content.text` is required if `html` is given (or auto-derived and flagged). Header allow-list only, no CR/LF anywhere. `category=marketing` requires `unsubscribe`. `from.email` must match a verified sender for the tenant. At most 50 recipients per message (A). Inline attachment bodies are accepted up to 256 KB (A), above that a `ref` is required.

Responses (REST `POST /v1/messages`):
- `202 Accepted`, `Location: /v1/messages/{message_id}`, body `{"message_id":"msg_01J…","state":"accepted","idempotency_key":"…","correlation_id":"…"}`. A replay returns the same body with `Idempotent-Replayed: true`.
- Errors use one shape `{"error":{"code","message","retryable","details":[…],"request_id"}}` and these codes: `validation_error` (422), `unauthenticated` (401), `forbidden` and `sender_not_allowed` (403), `payload_too_large` (413), `idempotency_conflict` (409), `rate_limited` (429 with `Retry-After`), `unavailable` (503 with `Retry-After`).
- The existing `POST /api/v1/baruapepe/sendmail` stays as a deprecated shim that maps into the new path and returns the old envelope plus the new `message_id`.

Other REST: `GET /v1/messages/{id}` (state, attempts, reason), `POST /v1/messages/{id}:cancel` (only before `sending`), `GET/PUT/DELETE /v1/suppressions/{email}`, `POST /v1/attachments` (pre-signed upload), `GET /healthz` (liveness), `GET /readyz`. gRPC mirrors this as `EmailService.Send / GetMessage / Cancel` with the same envelope in metadata.

### 3.2 Event: `EmailStateChanged` (schema `email.state.v1`)
Published to the Kafka topic `barua-pepe.events.v1` (key `message_id`; tenant and state carried as headers), or on the optional RabbitMQ binding to a topic exchange (`email.state`, routing key `email.<state>.<tenant_id>`), or POSTed to a registered callback (signed), or read back with `GET`. CloudEvents-compatible.
```json
{
  "specversion": "1.0", "id": "evt_01J…", "type": "email.delivered", "source": "barua-pepe",
  "time": "2026-10-07T12:00:03Z", "subject": "msg_01J…",
  "data": {
    "message_id": "msg_01J…", "idempotency_key": "…", "correlation_id": "…", "tenant_id": "t_42",
    "state": "delivered", "previous_state": "sent", "sequence": 4,
    "provider": "sendgrid", "provider_message_id": "…", "attempt": 1,
    "recipient": "a@example.org",
    "reason": {"code": "mailbox_full", "category": "soft_bounce", "retryable": false, "detail": "…"}
  }
}
```
`sequence` is monotonic per message so that consumers can drop out-of-order duplicates. Delivery is at-least-once. Consumers dedupe on `id`. `reason.code` comes from a closed taxonomy: `recipient_invalid`, `recipient_suppressed`, `mailbox_full`, `content_rejected`, `spam_blocked`, `provider_rejected_permanent`, `provider_unavailable`, `provider_rate_limited`, `outcome_unknown`, `attachment_blocked`, `policy_blocked`, `expired`, `cancelled`, `internal_error`.

### 3.3 Delivery-state model
```
 (intake) ──► accepted ──► queued ──► sending ──► sent ──► delivered
     │            │           │          │          ├────► bounced (hard | soft | block)
  rejected    suppressed   expired   outcome_unknown ├────► complained
 (not stored  (terminal)  (terminal)  (needs resolve)└────► failed (terminal)
  as message)                         ──► sent | failed | resend (capped)
```
- `accepted`: persisted, idempotency recorded. `queued`: handed to the work queue by the outbox. `sending`: a worker holds a lease and has written an attempt row before calling the provider. `sent`: provider returned acceptance (SMTP `250`, SendGrid `202`). `delivered`/`bounced`/`complained`: from provider webhooks or DSNs. `failed`: permanent rejection, or retries/expiry exhausted. `outcome_unknown`: the provider call failed ambiguously. It is reconciled by lookup and, if still unconfirmed at the deadline, resent (capped, counted; see 5.3). `suppressed` is a terminal pre-send decision.
- `delivered_unconfirmed` (terminal): a `sent` message with no feedback (no webhook, DSN or bounce) by the `feedback_window` (A: 72 h) is closed in this state by the reconciler. Every accepted message therefore reaches a terminal state without claiming a delivery that was never confirmed (SMTP acceptance is not delivery). **Late feedback:** a valid provider event that arrives after this closure does not change the state, because terminal messages never transition. It is stored in `webhook_receipts`, recorded as an `events` row and emitted as a `message.feedback` event marked `late` with the provider's own `occurred_at`, so callers can see the later evidence. Address-level effects still apply: a late hard bounce, complaint or unsubscribe inserts into `suppressions` exactly as an on-time one would.
- `opened`/`clicked` are recorded as events on a `sent` or `delivered` message, not as states.
- Transitions are guarded in SQL (`UPDATE … WHERE state IN (…)`) and each writes an `events` row and an outbox row in one transaction.

## 4. Data model (PostgreSQL sketch)
```sql
tenants(id, name, status, created_at)
senders(id, tenant_id, from_domain, from_address, dkim_status, spf_status, dmarc_status, verified_at)
credentials(id, tenant_id, kind, key_hash, scopes[], expires_at, last_used_at)       -- or an external IdP
messages(id, tenant_id, idempotency_key, request_hash, correlation_id, state, category, priority,
         from_address, subject_hash, body_ref, recipient_count, send_after, expires_at,
         attempts, next_attempt_at, lease_owner, lease_until, provider, provider_message_id,
         created_at, updated_at, UNIQUE(tenant_id, idempotency_key))
recipients(message_id, role, address, address_hash, state, last_reason_code)        -- per-recipient outcome
attempts(id, message_id, n, provider, started_at, finished_at, outcome, provider_status,
         error_code, request_id)                                                    -- journal written BEFORE the call
events(id, message_id, sequence, type, data jsonb, occurred_at, source)            -- append-only
outbox(id, topic, key, payload jsonb, created_at, published_at)
suppressions(tenant_id, address_hash, address_enc, reason, source_event_id, created_at, expires_at,
             PRIMARY KEY(tenant_id, address_hash))
webhook_receipts(provider, event_id, received_at, PRIMARY KEY(provider, event_id)) -- replay/dedupe
```
- Message bodies and attachments are not kept in hot tables. `body_ref` points to object storage with a configurable retention (A: 30 days), after which only metadata and `subject_hash` remain. Addresses are stored once for operational need and encrypted at rest. Logs carry hashes only.
- Retention: `events` 13 months, `attempts` 90 days, `webhook_receipts` 14 days, `outbox` rows deleted after publish plus 7 days.

## 5. Pipeline design

### 5.1 Intake
authenticate (tenant) → authorise `from` against `senders` → validate (schema, sizes, CR/LF, recipient count, attachment refs) → `INSERT messages … ON CONFLICT (tenant_id, idempotency_key)` → compare `request_hash` (replay returns the stored response) → `INSERT events(accepted), outbox(work)` → commit → `202`. Rate limiting (token bucket per tenant) runs before the insert. No Celery or broker call exists in the request path. If the database is down the response is 503, never 500, and readiness fails.

### 5.2 Work dispatch and claim
The outbox relay publishes `{message_id}` only (not the content) to the work queue, with priority and `send_after` handling. The worker claims with `UPDATE messages SET state='sending', lease_owner=…, lease_until=now()+interval WHERE id=… AND state IN ('queued','retry_wait')`. A lost lease (worker crash) is picked up by the reconciler. The work queue has **no TTL**. Staleness is decided by `expires_at` in the database.

### 5.3 Attempt, retry and unknown outcome
1. Check suppression (all recipients; partial suppression splits per recipient), expiry and tenant/provider rate limits.
2. Write an `attempts` row (`started`), then call the provider. Each call has connect and read timeouts (A: 5 s and 20 s) and the registry's circuit breaker.
3. Classify the result with one taxonomy shared by all adapters:
   - **accepted** → `sent`.
   - **permanent rejection** (SMTP 5xx, HTTP 4xx other than 408/429) → the recipient or message `failed`. No retry. Fail over to the next provider only when the rejection is provider-specific (auth, account, quota) and not content-specific.
   - **transient** (SMTP 4xx, HTTP 429/5xx before acceptance, connection refused, DNS) → retry with exponential backoff and full jitter (30 s, 2 m, 10 m, 1 h … capped), until `expires_at` or max attempts, then `failed(expired)`. Failover is allowed because nothing was accepted.
   - **ambiguous** (timeout after the request body was sent, connection reset mid-`DATA`, 5xx after acceptance) → `outcome_unknown`. No failover before reconciliation. Resolve via webhook or provider message-id lookup within a window (A: 24 h). If still unconfirmed at the deadline, **resend** (decision D6: a missed message is worse than a duplicate), capped (A: 2 resends) and counted, with an alert and an event; a resend happens only before `expires_at` when the caller set one. Default policy is `on_unknown_outcome=resend`.
4. Deterministic `Message-ID: <{message_id}@{sending-domain}>` is set on every attempt so that duplicate deliveries are at least detectable downstream.
5. After the call: write the attempt outcome, the state transition, the event and the outbox row in one transaction.

### 5.4 Poison messages and DLQ
Schema-invalid or unprocessable queue messages go to the dead-letter topic `barua-pepe.commands.dlq.v1` (queue `email.send.dlq` on the optional RabbitMQ binding) with origin topic, partition, offset, error and attempt-count headers (`x-death` on RabbitMQ) and are recorded in `events` (`failed`, `internal_error`). A replay CLI re-publishes them after a fix. The DLQ is monitored (alert on depth > 0 for 5 min) and has no consumer that discards. Retry delays are held in the database (`next_attempt_at`, polled with `FOR UPDATE SKIP LOCKED`) or in tiered retry topics or delay queues (ADR-3), never in per-message broker TTLs on the main queue.

### 5.5 MIME and content
A single `MimeBuilder` using `email.message.EmailMessage` (SMTP policy): `multipart/alternative` (text then html), `multipart/mixed` for attachments, RFC 2047 encoded names, `Date`, deterministic `Message-ID`, `List-Unsubscribe` and `List-Unsubscribe-Post: List-Unsubscribe=One-Click` for `marketing` (and recommended for bulk-like transactional), header allow-list, and CR/LF rejection. SMTP uses this output directly. HTTP providers receive the equivalent structured fields from the same internal `OutboundMessage`, so all providers render the same request the same way. Plain-text alternative is mandatory (derived from HTML if missing).

### 5.6 Provider plug-in model
```python
class ProviderPort(Protocol):
    name: str
    capabilities: Capabilities            # max_recipients, max_message_bytes, supports_batch, webhook_kind
    def submit(self, msg: OutboundMessage, ctx: SubmitContext) -> SubmitResult: ...   # returns provider_message_id
    def verify_webhook(self, headers, body) -> list[ProviderEvent]: ...
    def health(self) -> Health: ...
```
Adapters register through an entry point or an explicit registry dict keyed by name. Configuration is per provider: `PROVIDERS__sendgrid__api_key=…`, loaded from a secret store. Routing is declarative (per tenant): ordered provider list, failover rules, weights, and the IP pool or sub-user. Each provider has a circuit breaker (open on N consecutive transient failures, half-open probe) and its own concurrency and rate limits. Credentials are never logged. Rotation is supported by holding two versions in the secret and selecting by `kid`. Adding a provider means one adapter module plus a contract-test run against the shared adapter test suite (see `05-test-strategy.md`).

### 5.7 Webhooks and suppression
Receiver verifies the provider signature (SendGrid ECDSA signed event webhook with a timestamp tolerance, SES via SNS signature validation and subscription confirmation, Mailgun HMAC), rejects stale or replayed events (`webhook_receipts`), maps to `delivered|bounced|complained|opened|clicked`, and applies transitions idempotently and out-of-order-safe (state precedence plus `occurred_at`). Events for a message already in a terminal state (including `delivered_unconfirmed`) are not applied as transitions; they follow the late-feedback rule under `delivered_unconfirmed` in the state model. Hard bounces, spam complaints and provider-level unsubscribes insert into `suppressions` (scoped per tenant, with reason and source). The send worker consults suppressions before every attempt. Soft bounces count toward a threshold before suppression. Manual removal needs an authorised API call and is audited.

### 5.8 Attachments
`POST /v1/attachments` returns a pre-signed upload URL. The service enforces per-file (A: 10 MB) and per-message (A: 20 MB) limits, a content-type allow-list verified by magic bytes (not the declared type), blocked executables, and ClamAV (or a managed scanner) before the attachment becomes `ready`. A message can reference only `ready` attachments belonging to the same tenant. The worker streams from storage when building MIME. Inline base64 is accepted only below a small threshold and goes through the same scan. Objects expire with the message's retention.

### 5.9 Templating (ADR-4)
Recommended default: the gateway does not render templates, and niosys (which owns preferences, locale and content) sends final `text` and `html`. If rendering stays in the gateway, use a sandboxed Jinja2 environment (`SandboxedEnvironment`, autoescape on for HTML, no filesystem loader outside a template store, data size limits, render timeout, templates versioned and immutable, locale fallback chain). Never render caller-supplied template source.

## 6. Security model
- **Authn:** OAuth2 client-credentials JWT (JWKS-verified, `aud`, short expiry) or mTLS from inside the mesh; per-tenant API keys (hashed, scoped, rotatable) for non-platform callers. No shared Basic credential. Broker access uses per-service credentials, with vhost or topic ACLs per tenant for AMQP intake.
- **Authz:** scopes `email:send`, `email:read`, `suppression:write`, `admin`. A sender may only use `from` addresses of domains verified for its tenant. SPF, DKIM and DMARC: the gateway verifies at onboarding that DNS records for the sending domain are in place (provider-side DKIM or its own signing), and refuses to send otherwise. The playbook (who publishes which record) is documented per provider.
- **Input:** hard limits (body 1 MB without attachments, recipients 50, subject 998 octets and no CR/LF, header allow-list), validated at both edges (REST and broker consumer) by the same schema.
- **Data:** PII minimisation (hashes in logs and metrics labels, never addresses), encryption at rest for message addresses and bodies, retention jobs, loguru `diagnose=False`, Sentry `send_default_pii=False` with a scrubber, Celery events or message payloads never carry content.
- **Webhook ingress:** separate deployment, signature and timestamp checks, per-provider allow-listed source ranges when documented, no authenticated data path to the send side.
- **Supply chain:** pinned, locked and audited dependencies, a non-root minimal image, read-only filesystem, no `latest` tags, SBOM, and secrets from the platform secret store (not `.env`).
- **Abuse controls:** per-tenant send and recipient quotas, complaint-rate circuit breaker (auto-pause a tenant when complaints exceed a threshold), and audit log for credential and sender changes.

## 7. Scaling model and bottlenecks
- Stateless intake and workers scale horizontally. Autoscale workers on `queue depth / drain rate` (KEDA on Kafka consumer-group lag; queue depth on RabbitMQ) and the API on CPU/RPS.
- Bottlenecks, in expected order: (1) provider rate limits and per-IP warm-up ceilings (control with per-provider token buckets and tenant fair-share queues), (2) PostgreSQL write amplification (about 5 to 6 row writes per message: message, attempt, events, outbox, recipients. Batch outbox relays, use partitioned `events`, size connection pools, and consider `UNLOGGED` only for non-authoritative caches), (3) SMTP connection setup (pool and reuse connections, per-worker pool sized to relay limits), (4) object storage and AV throughput for attachments.
- Priority lanes: `transactional-high`, `transactional`, `bulk`, as separate queues so bulk cannot starve OTPs. Per-tenant fairness uses weighted dequeue or per-tenant sub-queues above a threshold.
- Batching: multi-recipient sends are split by provider limits. The batch endpoint accepts up to N independent messages (each with its own idempotency key) in one request. Providers with batch APIs are used where capabilities say so.
- Capacity target (A): 300 msg/s sustained and 2 000 msg/s burst per region with the 5 s TTL gone and the queue absorbing bursts. The load test in `05-test-strategy.md` validates it.
- Warm-up: per-IP-pool daily ramp schedule enforced in the rate limiter (for example 50, 100, 500, 1 000, 5 000 per day). Applies only if the platform operates its own IPs (Q-BAR-06).

## 8. Observability
- **Correlation:** `correlation_id` and `message_id` on every log line, span and event. W3C `traceparent` propagated through REST, broker headers and outbox rows. OpenTelemetry for traces and metrics, Prometheus-compatible export.
- **Metrics (RED plus pipeline):** `intake_requests_total{tenant,code}`, `intake_latency_seconds`, `messages_in_state{state}` (gauge from the DB), `time_in_state_seconds{state}`, `attempts_total{provider,outcome}`, `provider_latency_seconds{provider}`, `provider_circuit_state{provider}`, `queue_depth{queue}` and oldest-message age, `outbox_lag_seconds`, `webhook_events_total{provider,type,result}`, `suppressions_total{reason}`, `duplicate_suppressed_total`, `outcome_unknown_total`, `dlq_depth`. Tenant label only when cardinality is bounded.
- **Logs:** structured JSON to stdout through one tested formatter; recipient hashes; no bodies.
- **Health:** `/healthz` (process alive), `/readyz` (DB, broker, provider registry has at least one healthy provider).
- **Alerts:** oldest queued age > SLO, `outcome_unknown` rate, DLQ depth, outbox lag, bounce or complaint rate per tenant, circuit open, reconciler finds messages past SLA.

## 9. SLO suggestions (to be ratified, Q-BAR-12)
| SLI | Target |
|---|---|
| Intake availability (non-5xx / total, excluding 4xx) | 99.95% monthly |
| Intake latency p99 | < 300 ms |
| Accepted to provider hand-off (`sent`), transactional, p95 / p99 | < 15 s / < 60 s |
| Accepted messages that reach a terminal state | 100% (reconciler alert on any violation) |
| Silent loss (accepted but untracked) | 0 |
| Duplicate provider submissions | < 0.01% of sends |
| State event publish lag p95 | < 5 s |
| Webhook to state-update p95 | < 10 s |

## 10. ADR-worthy decisions

| ADR | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Worker runtime and public queue contract | (a) keep Celery and make its message the contract; (b) Celery internally, with a separate public broker/gRPC contract mapped to it; (c) native consumer behind the broker port (Kafka first, for example confluent-kafka or FastStream; aio-pika only for the optional RabbitMQ binding) with no Celery | (c) in the end state, (b) as the migration step. Celery's protocol is private, python-specific and awkward for outbox and lease semantics. **Kafka is the first binding (decision D5);** the port keeps RabbitMQ and others pluggable. |
| 2 | State store | PostgreSQL; DynamoDB; Redis only; keep stateless | PostgreSQL (transactions for state plus outbox, `SKIP LOCKED`, familiar ops). Redis only for ephemeral rate limiting. |
| 3 | Retry delay mechanism | tiered retry topics (Kafka) or delay queues (RabbitMQ TTL+DLX); delayed-message exchange plugin; DB `next_attempt_at` | DB-driven `next_attempt_at` with a scheduler loop, since state is already in Postgres and per-message TTL on the main queue is what caused BAR-007. |
| 4 | Where templating lives | niosys renders; gateway renders (sandboxed Jinja2); provider-side templates | niosys renders by default. Revisit if other callers need server-side rendering. |
| 5 | Attachment handling | inline base64; claim-check in object storage with AV; provider-hosted | claim-check with AV scan; inline only below a small threshold. |
| 6 | Service authn | shared Basic; per-tenant API keys; OAuth2/JWT; mTLS | JWT (client credentials) as primary, API keys for external callers, mTLS optional at the mesh. Remove Basic. |
| 7 | Webhook receiver placement | in the API app; separate deployable | separate deployable, with its own credentials and no path to the send side. |
| 8 | Outbound state delivery | broker topic only; REST callbacks; both | broker topic as the primary, optional signed callback per tenant, `GET` as the fallback. All carry the same `EmailStateChanged` envelope. |
| 9 | Unknown-outcome policy | always hold; always resend; per-message choice | per-message choice, default `resend` after the reconcile deadline, capped and counted (decision D6), with tenant defaults. |
| 10 | Python and framework baseline | 3.10; 3.12; 3.13 | 3.12 (LTS-like support window, wheels available), tested also on 3.13. |

## 11. Migration path from today's code

Each step is shippable and leaves the existing REST route working.
1. **Hotfix pass (no design change):** BAR-001/002 config and credentials, BAR-009..013 SMTP, BAR-019/020 logging and lifecycle, BAR-033/034/035 container, CI and lock. Replace the queue TTL with a versioned queue (BAR-007) using the migration steps already described in README.
2. **Contract and state:** add Postgres and Alembic, `messages`/`events`/`outbox`. Put the new `POST /v1/messages` beside the old route. Mint `message_id`, require `Idempotency-Key` on the new route, return 503 on dependency failure, and keep Celery behind the outbox relay so workers change little. Publish `EmailStateChanged` from the worker transitions.
3. **Worker rewrite on the new core:** introduce `ProviderPort`, the registry, `MimeBuilder`, the attempt journal, the taxonomy, retry and DLQ replay. Move the existing adapters behind it. Delete `mail_error_task`, `mail_analytics_task`, the stubs and the Mailchimp adapter (or port it properly).
4. **Native transports:** add the broker intake consumer (Kafka first, behind the broker port) and the gRPC edge on the same application service. Retire the Celery message as a public contract (ADR-1).
5. **Feedback loop:** webhook receiver, suppressions, unsubscribe headers, attachment service.
6. **Tenancy and reputation:** JWT/API-key authn, sender verification, per-tenant limits, warm-up, complaint circuit breaker.
7. **Retire:** `sendmail` legacy route after callers (niosys, and niosys-v2 if it ever calls this service) have moved. Remove Basic auth.
