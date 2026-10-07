> **Status: Proposed. Discovery output dated 2026-10-07; not accepted architecture.** Describes the code as inspected on that date and a proposal for its replacement. Decisions are tracked in the ADR index and open-question log.

> **Answered on 2026-10-07:** Q-BAR-01 barua-pepe is **not** running on default credentials (they are for local development and tests only); whether it carries real traffic is still unanswered. Q-BAR-04 the broker is Kafka (services stay broker-pluggable); persistence default PostgreSQL still unconfirmed. Q-BAR-02, 03, 05 to 14 remain open.

# barua-pepe: open questions (humans only)

Format: question, why it matters, options, recommended default. The five that block the most work are marked **BLOCKER**.

## Q-BAR-01 (BLOCKER): Is barua-pepe running anywhere with real traffic today?
- **Why:** it decides the urgency and the method of the Phase 0 fixes (BAR-001 default credentials, BAR-007 queue TTL, BAR-009..012 SMTP). A live deployment needs a migration plan for queue arguments (RabbitMQ rejects argument changes) and a credential rotation.
- **Options:** (a) not deployed (greenfield changes allowed); (b) deployed with one caller; (c) deployed with several callers.
- **Default:** assume (b). Ship the hotfixes behind a short deprecation note, rotate credentials, and leave the old route in place.

## Q-BAR-02 (BLOCKER): Who renders email content, niosys or barua-pepe?
- **Why:** it determines whether the gateway needs a template store, localisation and sandboxing (BAR-028), and how large the attack surface (SSTI) is.
- **Options:** (a) niosys renders and sends final text and HTML; (b) the gateway renders from versioned templates; (c) providers' own template systems.
- **Default:** (a). Revisit if non-niosys callers need server-side rendering.

## Q-BAR-03 (BLOCKER): Who owns suppression and unsubscribe state, the gateway or niosys?
- **Why:** niosys owns recipient preferences. The gateway sees bounces, complaints and provider unsubscribes first. Two sources of truth would drift and break RFC 8058 one-click handling (BAR-026, BAR-027).
- **Options:** (a) gateway owns delivery-driven suppression (hard bounce, complaint) and exposes it, niosys owns preference-driven opt-outs, and the gateway checks both; (b) everything in niosys with the gateway forwarding events; (c) everything in the gateway.
- **Default:** (a), with the gateway publishing `suppressed` and complaint events that niosys consumes into preferences.

## Q-BAR-04 (BLOCKER): What persistence and broker may the platform standardise on?
- **Why:** there is no database today. The state machine, idempotency, outbox and suppression (Phase 1) all need one. The broker choice decides the native transport (ADR-1).
- **Options:** persistence: PostgreSQL, MySQL, DynamoDB. Broker: RabbitMQ (today), Kafka, SQS/SNS, NATS.
- **Default:** PostgreSQL and RabbitMQ (already in use here), with the contract kept broker-neutral.

## Q-BAR-05 (BLOCKER): What is the tenancy and caller identity model?
- **Why:** today one shared Basic credential exists (BAR-001, BAR-003). Rate limits, sender verification, suppression scope and billing need a tenant. niosys may be the only caller or one of many.
- **Options:** (a) a single caller (niosys) authenticated by mTLS or JWT, with tenant carried as a signed claim; (b) many tenants with their own API keys and verified domains; (c) deployment per tenant.
- **Default:** (a) now, designed so (b) is additive: `tenant_id` in the contract from day one.

## Q-BAR-06: Does the platform run its own sending IPs or use provider shared pools only?
- **Why:** warm-up, IP-pool and reputation controls (BAR-029) are only the platform's job with dedicated IPs.
- **Options:** shared provider pools; dedicated IPs at one provider; own MTA.
- **Default:** shared pools or provider dedicated IP, with limits enforced in the gateway. No warm-up engine until dedicated IPs exist.

## Q-BAR-07: Is the 5 s queue TTL with dead-lettering intentional?
- **Why:** commit `963bf07` preserves it as a "deployed contract" and a test pins it. It expires accepted mail under any backlog (BAR-007). Perhaps it was an intended "drop stale OTPs" rule.
- **Options:** (a) bug, remove it and use `expires_at` per message; (b) intended for time-sensitive mail, make it a per-message `expires_at` and a visible `expired` state; (c) keep as is.
- **Default:** (b). Expiry belongs to the message and is reported, never silent.

## Q-BAR-08: Attachment policy
- **Why:** size limits, allowed types and scanning shape storage and cost (BAR-004, BAR-030).
- **Options:** max per file (5, 10, 25 MB) and per message; allowed MIME list; ClamAV in-cluster or a managed scanner; retention.
- **Default:** 10 MB per file, 20 MB per message, allow-list of common document and image types by magic bytes, ClamAV, retention 30 days.

## Q-BAR-09: How should results reach callers, and with what delivery guarantee?
- **Why:** the contract (BAR-021, BAR-022) needs one primary route. Both niosys and ujumbe should behave the same.
- **Options:** broker topic only; signed webhook callbacks; polling `GET`; all three.
- **Default:** a broker topic as primary, `GET` always available, optional signed callback. At-least-once with `id` and `sequence` for dedupe.

## Q-BAR-10: Python and runtime baseline
- **Why:** Python 3.10 reaches end of life on 2026-10-31 and the lock does not resolve (BAR-035).
- **Options:** 3.12, 3.13; keep Celery or replace it (ADR-1).
- **Default:** 3.12 now, 3.13 in CI; Celery kept only until the native consumer lands.

## Q-BAR-11: Transactional only, or also bulk and marketing mail?
- **Why:** marketing mail makes RFC 8058 one-click, consent evidence, complaint-rate controls and priority isolation mandatory rather than nice to have (BAR-027, BAR-029).
- **Options:** transactional only; transactional plus marketing categories; separate deployments per category.
- **Default:** both categories in the contract, separate queues and IP/provider pools, marketing requires `unsubscribe`.

## Q-BAR-12: SLO targets and operational ownership
- **Why:** the targets in `03-target-design.md` section 9 are proposals. Capacity (300 msg/s sustained, 2 000 burst) is a guess.
- **Options:** supply real peak volumes and latency expectations (for example OTP delivery within 30 s).
- **Default:** keep the proposed numbers until real traffic data exists.

## Q-BAR-13: Data retention and privacy constraints
- **Why:** the state store will hold addresses and optionally bodies. Retention and encryption rules (GDPR/Kenyan DPA or similar) change the schema and jobs (BAR-005).
- **Options:** keep metadata only; keep bodies N days; no bodies.
- **Default:** metadata 13 months, bodies and attachments 30 days, addresses encrypted at rest and hashed in logs.

## Q-BAR-14: Repository hygiene decisions
- **Why:** the repo mirrors to Bitbucket and GitLab through an unpinned third-party action that holds tokens, has no LICENSE, and uses semantic-release and Danger tooling written for Node (BAR-034, BAR-038).
- **Options:** keep mirrors, pin or remove the action; add a LICENSE (which); keep Danger or replace it with plain workflow checks.
- **Default:** pin the mirror action to a commit SHA (or drop the mirrors), add the same LICENSE as niosys, and keep semantic-release but declare it explicitly.
