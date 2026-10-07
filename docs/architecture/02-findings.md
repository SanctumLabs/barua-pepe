> **Status: Proposed. Discovery output dated 2026-10-07; not accepted architecture.** Describes the code as inspected on that date and a proposal for its replacement. Decisions are tracked in the ADR index and open-question log.

# barua-pepe: findings register

Severity: P0 data loss, security-critical or outage. P1 serious. P2 important. P3 minor.
V = Verified (I read and traced the code, and probed it where noted). S = Suspected (reasoned from the code and library behaviour, not run end to end).
Probes were run from a scratch directory against the repo with a Python 3.11 venv built from the locked default set. Nothing in the repo was changed.
Issues filed: epics #858 to #864, children #865 to #895 (see `07-issues-filed.md`). Existing GitHub issues #841 to #844 are CLOSED and cover the canonical request contract, the dispatch seam, the delivery policy and the CC/BCC envelope. None of the findings below duplicates them. They are referenced where relevant.

## Register

| ID | Sev | Category | Title | Evidence | V/S | Issue |
|---|---|---|---|---|---|---|
| BAR-001 | P0 | security | Default shared API credentials are accepted, and production validation ignores them | `app/config.py:63-64`, `:66-95`; `app/services/auth/auth_service.py:14-26` | V | #865 |
| BAR-002 | P1 | security | Production config validation is inert: it reads `ENVIRONMENT` while everything else uses `ENV` | `app/config.py:38,72`; `app/logger.py:57,64,67`; `asgi_server.py:6`; `.env.example:17` | V | #865 |
| BAR-003 | P1 | security | No tenant model or authz, any caller can send as any From, no sender-domain verification, SPF/DKIM/DMARC ownership undocumented | `app/api/mailer/dto.py:35`; `app/api/mailer/routes.py:25-58`; `README.md` | V | #888 |
| BAR-004 | P2 | security | No limits or validation on attachment size, base64, MIME type, filename, recipient count, subject or message length, or CR/LF in subject and names | `app/domain/entities/email_attachment.py:14-37`; `email_request.py:24-58` | V | #884 |
| BAR-005 | P2 | security | PII and secrets leak through logs, result backend, exception text and Celery events | `routes.py:52`; `smtp_proxy.py:131-140`; `logger.py:94-102`; `celery_app.py:80,105` | V (logs, results) / S (diagnose, events) | #889 |
| BAR-006 | P2 | security | `/metrics`, `/docs`, `/openapi.json` are unauthenticated on the service port; Flower has no auth; RabbitMQ `guest` | `app/api/monitoring/routes.py:21-24`; `app/config.py:39`; `docker-compose.yml:5-10,24-28` | V | #889 |
| BAR-007 | P1 | reliability | Primary queues have a 5 s message TTL that dead-letters accepted emails whenever backlog exceeds 5 s | `app/worker/queues.py:51-62`; `docker/rabbitmq_definitions.json:15-23,32-41`; `tests/tasks/test_queues_dlx.py:7-18` | V (config) / S (consequence) | #866 |
| BAR-008 | P1 | reliability | No idempotency: client retries, worker loss, time-limit kills and Celery retries can all send the same email twice | `celery_app.py:82-85,89-97`; `mail_sending_task.py:18-71`; `routes.py:25-58` | V | #875 |
| BAR-009 | P1 | bug | SMTP attachments are corrupted: double base64 for one attachment, only the last survives for several, and duplicate headers | `app/services/mail/smtp_proxy.py:97-115` | V (probe) | #867 |
| BAR-010 | P1 | bug | SMTP always sends `text/plain` (HTML shown as source), ignores display names and attachment `type`, and adds no Message-ID or Date. HTML detection differs across providers. | `smtp_proxy.py:88-95,112`; `sendgrid_email_service.py:61`; `mailchimp_email_service.py:72` | V (probe) | #867 |
| BAR-011 | P1 | bug | SMTP partial recipient refusal is reported as success. `smtplib` returns the refused dict and the code ignores it. | `smtp_proxy.py:123-134` | V (probe) | #867 |
| BAR-012 | P1 | bug | SMTP auth runs only in the API process (the worker never logs in), reconnect drops the session, login failure is swallowed, auth is skipped without TLS or SSL, and API startup fails if SMTP is down | `app/__init__.py:29-30`; `smtp_proxy.py:31-60,120-122` | V | #868 |
| BAR-013 | P2 | reliability | No network timeouts on SMTP or the SendGrid client, so hung calls run until the 120 s hard kill, which then requeues (duplicates) | `smtp_proxy.py:38-40`; `sendgrid_email_service.py:46,88`; `celery_app.py:93` | V (SMTP) / S (SendGrid default) | #868 |
| BAR-014 | P1 | reliability | The error path discards messages: `mail_error_task` logs and drops the payload; unknown outcomes and exhausted retries end there with no store, no replay and no state | `app/tasks/mail_error_task.py:24-38`; `mail_sending_task.py:50-56,65-67` | V | #881 |
| BAR-015 | P2 | reliability | Error taxonomy is wrong: permanent rejections are retried 3x; connection-refused and caller-caused header errors count as "unknown"; transient SMTP 4xx count as definitive | `mail_sending_task.py:58-71`; `smtp_proxy.py:161-176` | V (probe) | #881 |
| BAR-016 | P1 | reliability | API availability: blocking `apply_async` inside an `async` handler. Observed about 19 s per request with broker and Redis down, then a generic 500 with no 503. No publisher confirms. | `routes.py:44`; `celery_email_dispatcher.py:13`; `celery_app.py:38,65-67` | V (probe) / S (confirms) | #872 |
| BAR-017 | P2 | reliability | Broker and result-backend configuration defects: invalid default URL, unescaped credentials, Sentinel options on a plain `redis://` URL, `visibility_timeout` irrelevant to AMQP, `task_protocol=1`, unused settings | `celery_app.py:21-44,79`; `config.py:54`; `.env.example:46-52` | V | #882 |
| BAR-018 | P2 | tech-debt | Worker registers tasks only by importing the whole FastAPI app; dead code (`mail_analytics_task` unregistered, analytics queue, Mailchimp provider, stub callback task, unused deps) | `celery_app.py:65-67`; `app/tasks/__init__.py`; `mail_analytics_task.py`; `mailchimp_email_service.py` | V (probe) | #882 |
| BAR-019 | P1 | bug | Production JSON logging is broken: the custom format string raises `KeyError '"time"'` in loguru for every record. Messages are also duplicated across the per-level sinks. | `app/logger.py:72-102` | V (probe) | #869 |
| BAR-020 | P2 | bug | App lifecycle defects: `on_teardown` is not a FastAPI parameter, so shutdown never runs; `@logger.catch` sits above `@router.post` and has no effect; duplicate Sentry init and an unused `asgi_app`; server-generated request id ignores inbound correlation | `app/__init__.py:53-54`; `routes.py:17-18`; `middleware.py:18-27,36` | V | #869 |
| BAR-021 | P1 | feature | Platform contract missing: no message id, no client idempotency key, no correlation id returned or accepted, ad hoc error codes (400 vs 422), no versioning | `routes.py:46-50`; `dto.py`; `exception_handlers.py:60-77` | V | #874 |
| BAR-022 | P1 | feature | No delivery-state model: no DB, no state machine, no status query, no outbound events or callbacks | whole repo; `CONTEXT.md` terms never persisted | V | #876, #877 |
| BAR-023 | P1 | feature | The only inbound queue contract is Celery's private task message (`mail_sending_task` kwargs). Other services cannot publish natively. | `celery_email_dispatcher.py:13-18`; `celery_app.py:50-63` | V | #878 |
| BAR-024 | P2 | tech-debt | Provider selection hard-coded; one shared `MAIL_API_TOKEN`; no registry, health, circuit breaker or credential rotation | `mailer.py:25-32`; `config.py:51-52`; `sendgrid_email_service.py:38-46` | V | #879 |
| BAR-025 | P1 | feature | No provider webhook ingestion (bounce, complaint, delivery, open, click) and no signature verification | grep over repo: no hits | V | #885 |
| BAR-026 | P1 | feature | No suppression list. Hard bounces and complaints are never remembered, so reputation risk grows with every resend. | n/a | V | #886 |
| BAR-027 | P2 | feature | No unsubscribe support (List-Unsubscribe, RFC 8058 one-click) | n/a | V | #887 |
| BAR-028 | P2 | feature | No templating, localisation or plain-text alternative. Callers must pre-render, and the owner is undecided. | n/a | V | #883 |
| BAR-029 | P2 | scalability | No sending-reputation controls: the only throttle is Celery `rate_limit` per worker instance; no per-tenant or per-provider limits, warm-up or IP pools | `celery_app.py:89-97` | V | #890 |
| BAR-030 | P2 | scalability | Attachments travel inline (base64) in broker messages and are never stored or scanned; there is no claim-check pattern or AV | `celery_email_dispatcher.py:13-18`; `email_attachment.py` | V | #884 |
| BAR-031 | P2 | scalability | Throughput model: one task per email, no batching, fixed concurrency 5, result-backend write per send, SMTP connection per child process (children recycled every 100 tasks) | `celery_app.py:93-102`; `Makefile:14-22` | V | #880 |
| BAR-032 | P2 | observability | Send counters are incremented in workers but `/metrics` is served by the API, so they read 0. `/healthz` is static (no readiness). The event exporter lives in every API process. | `app/metrics.py:71-82`; `mail_sending_task.py:40,45`; `app/__init__.py:14,33`; `monitoring/routes.py:13-18` | V | #891 |
| BAR-033 | P1 | ops | Dockerfile cannot build (`pipenv lock -r` removed), ignores `Pipfile.lock`, uses Python 3.10.5 (2022), runs uvicorn `reload=True` by default, has no HEALTHCHECK or worker entrypoint; compose uses RabbitMQ 3.7.9 (EOL) and `:latest` images | `Dockerfile:1,17-19,25`; `asgi_server.py:6-10`; `docker-compose.yml:5,15,24,35` | V (probe) | #870 |
| BAR-034 | P1 | ci | CI is broken or gated incorrectly: Lint exits 4; Tests and Docker hang off Lint through `workflow_run` and test the default branch rather than the PR head; Slack waits for a non-existent "Test"; Sentry waits for a non-existent "Build"; Danger runs yarn in a Python repo; CodeQL v2 | `.github/workflows/*.yml`; `Makefile:30-31` | V | #871 |
| BAR-035 | P2 | deps | Lock inconsistent (`pip install` fails to resolve); `develop` section pins vulnerable older packages; `ecdsa` advisory; Python 3.10 EOL 2026-10-31; Pipfile fully unpinned; unused dependencies | `Pipfile.lock`; `Pipfile:1-37` | V (pip, pip-audit) | #873 |
| BAR-036 | P3 | tech-debt | Pydantic v1-style APIs on Pydantic 2 (`validator`, `root_validator`, `.dict()`, `.parse_obj()`, `schema_extra`, `GenericModel`); v1 error type `value_error.missing`; FastAPI `on_startup` | `domain/entities/*.py`; `dto.py:5-40`; `exception_handlers.py:16` | V | #894 |
| BAR-037 | P2 | testing | Tests are mock-heavy and miss the defects above: auth is overridden, SMTP MIME composition is only checked for CC/BCC, no prod-logging, config or attachment tests, no contract or provider-fake tests; the integration test needs Docker | `tests/__init__.py:21-23`; `tests/services/mail/test_provider_outcomes.py`; coverage report | V | #893 |
| BAR-038 | P3 | docs | Documentation drift and strays: README names missing files (`constants.py`, `make run-worker`), conflicting container ports (4000, 5000, 6000), `MANIFEST.in` references missing dirs, stray root `.toml`, no LICENSE, `.dockerignore` omits `.git`, `tests` and caches so `COPY . .` ships them | `README.md`; `MANIFEST.in`; `.toml`; `.gitignore` | V | #895 |

## Detail

### BAR-001 (P0, security): default API credentials, validator blind to them
`Config.username`/`password` default to `barua-pepe-user`/`barua-pepe-password` (`config.py:63-64`). `get_current_auth` compares against exactly these values (`auth_service.py:14-26`). `validate_production_settings()` checks only SMTP credentials and `MAIL_API_TOKEN` (`config.py:77-92`). It never looks at `username`/`password`. I ran `Config()` with `ENVIRONMENT=production` and SMTP disabled plus an API token, and the validator passed with the default API credentials. The load test file `tests/loadtest/http_load.py:5-6` also embeds them.
- Impact: a deployment that forgets `USERNAME`/`PASSWORD` is an open authenticated relay with a publicly known password. Any caller can send phishing mail from any From address (BAR-003) through the owner's SMTP or SendGrid reputation.
- Fix: fail startup unless both are set and non-default in every non-test environment. Remove the defaults entirely. The longer-term fix is BAR-003.

### BAR-002 (P1, security): `ENV` vs `ENVIRONMENT`
`logger.py`, `asgi_server.py` and `.env.example` use `ENV`. `Config.environment` (pydantic-settings) maps to `ENVIRONMENT`. I ran `Config()` with `ENV=production` only, and `environment` stayed `development`. The validator returns immediately (`config.py:72-73`), so the documented production switch disables the production checks.
- Fix: one variable, read through `Config` only. Validate by default (opt out for dev, not opt in for prod).

### BAR-003 (P1, security): no tenancy, authz or sender verification
One shared Basic credential gates the whole API. The sender is taken from the request body (`dto.py:35`) and no code checks it against anything. There is no per-caller identity in logs or metrics. SPF, DKIM and DMARC responsibilities are not described: with SMTP they sit with the relay, with SendGrid they need domain authentication, and the gateway should refuse From domains it does not own. Related: BAR-001.

### BAR-004 (P2, security): unbounded and unvalidated input
`EmailAttachment.content` only has to be non-empty. I submitted a 20 MB non-base64 attachment with type `nonsense`, and validation accepted it (the request failed later only because no broker was available). `type` is a free string. `filename` is only non-empty and flows into `Content-Disposition` (Python's stdlib raises `HeaderParseError` for CR/LF, but the error is mapped to "unknown outcome", see BAR-015). Subject, message and sender name have no length or CR/LF checks. There is no cap on recipients or request body size. The effect is memory pressure on the API, broker and worker, plus poison messages.

### BAR-005 (P2, security): PII and secrets in logs and results
Verified: `routes.py:52` logs the full recipient list on failure. `smtp_proxy.py:133` puts sender and recipient dicts into the task result (stored in the result backend). `smtp_proxy.py:139` puts them into an exception message, which `@log.catch` and Sentry then log. `middleware.py:50,55` logs the full URL. Suspected: `log.add(...)` does not set `diagnose=False`, and loguru's default `diagnose=True` renders local variable values in tracebacks (message bodies, base64 attachments, SMTP password inside `login`). `worker_send_task_events` and `task_send_sent_event` make Celery events carry task arguments, visible to Flower (no auth in compose). The Oct 2026 commits `3297f07` and `e80df7f` removed some PII from logs, but not these paths.

### BAR-006 (P2, security): exposed endpoints and infra defaults
`/metrics` and `/healthz` are mounted outside the auth dependency (`app/__init__.py:59-62`). `/docs`, `/redoc` and the OpenAPI schema are on unless `DOCS_DISABLED`. Compose runs Flower unauthenticated and RabbitMQ with `guest:guest` (also baked into `.env.example` and `celery_app.py:23-24` defaults).

### BAR-007 (P1, reliability): 5 s TTL on the primary queue
`dead_letter_queue_option` sets `x-message-ttl: 5000` with a DLX on both `barua-queue` and `barua-analytics-queue` (`queues.py:51-62`). RabbitMQ expires any message still unconsumed after 5 s and dead-letters it to `barua-error-queue`. With `rate_limit=10/s` per worker instance and concurrency 5 (`Makefile:14`), a burst of 100 mails already exceeds the TTL for the tail. A worker outage longer than 5 s does the same. The message then sits in the error queue (no consumer, or a consumer that discards it, BAR-014). The Celery task name travels in the message headers, so a worker started with `-Q barua-error-queue` (as `make run-error-worker` does) would execute the expired `mail_sending_task` messages (Suspected; not run). The behaviour depends on which workers run. Commit `963bf07` preserves it on purpose as the "deployed contract", so whether it is intended needs a human answer (Q-BAR-07). RabbitMQ queue arguments are immutable, so changing it needs a versioned replacement queue.

### BAR-008 (P1, reliability): no idempotency
There is no idempotency key and no deduplication store. Duplicates can come from:
- client retry after a timeout or 5xx on the route,
- `task_acks_late` plus `task_reject_on_worker_lost` redelivering a task whose SMTP `DATA` already succeeded,
- a hard `time_limit=120` kill while SMTP is hung (BAR-013),
- `self.retry(...)` after an exception that happened after the provider accepted the message (for example in the result handling).
The team's own unknown-outcome rule (no retry, no cross-provider failover) shows awareness of the risk, but it is applied only to errors raised by the provider, not to infrastructure-level redelivery.

### BAR-009 to BAR-011 (P1, SMTP correctness; one issue)
I drove `SmtpServer.send_email` with a mocked connection (`probe/p1.py`, `p4.py`):
- A single attachment whose `content` is already base64 is sent as `base64(base64(content))`. The recipient decodes to the original base64 text, not the file (`smtp_proxy.py:104-107`).
- With two attachments only one MIME part is created outside the loop (`:98-99`). The payload of the last one wins. The first is dropped, and the part carries duplicated `Content-Transfer-Encoding` and `Content-Disposition` headers.
- Every attachment is `application/octet-stream` (the `type` field is ignored), and the filename is placed unquoted (`filename= name`).
- The body is always `MIMEText(message, "plain")`. A message such as `<html><body>hello</body></html>` is delivered as visible source. SendGrid and Mailchimp use `"<html" in message`, a case-sensitive substring test, which treats `<HTML>` or an HTML fragment as plain text. The three providers therefore render the same request differently.
- `From`/`To`/`Cc` ignore display names. There is no Message-ID, Date or Reply-To.
- `sendmail()` ignores the return value. When some recipients are refused, `smtplib` returns a dict of failures without raising, and the code reports `success: True` for the whole message.
- Fix: rebuild with `email.message.EmailMessage` (policy `SMTP`), and one shared MIME or HTML rule.

### BAR-012 (P1, reliability): SMTP session and auth
`SmtpServer().login()` is called only in `on_startup` of the FastAPI process (`app/__init__.py:30`). The API never sends mail. The Celery worker creates its own `SmtpServer()` on first send and never logs in, so an SMTP relay that needs auth rejects every send (as a definitive rejection, which falls over to SendGrid, so the failure is silent). `login()` authenticates only inside `if mail_use_tls` or `if mail_use_ssl`. It also swallows exceptions and calls `quit()` (`:46-60`). The reconnect path (`:120-122`) calls `connect()` without EHLO, STARTTLS or login. The constructor opens a socket at instantiation (`:36-40`), so API startup aborts when SMTP is down. This also holds a connection open in a process that never uses it.

### BAR-013 (P2): no timeouts
`smtplib.SMTP(host, port)` is built without `timeout`. The SendGrid client is created with default settings. Provider calls can hang until the 60 s soft limit (the task catches `SoftTimeLimitExceeded` as a generic exception and retries) or the 120 s hard kill, after which `task_reject_on_worker_lost` redelivers the message and may send it twice.

### BAR-014 and BAR-015 (P1/P2): error pipeline
`mail_error_task` takes `data` but uses only `len(data["recipients"])` and a counter (`mail_error_task.py:33-38`). A message that reaches it (invalid payload, unknown outcome, retries exhausted) is acked and gone. The README describes a "final sink", but nothing stores or replays it. Taxonomy problems:
- `EmailSendingException` (both providers explicitly rejected, for example an invalid recipient or a 401 from SendGrid) lands in the generic branch and is retried three times with 30, 60 and 120 s backoff.
- `SMTPServerDisconnected`, `ConnectionRefusedError` and similar are not in `definitive_rejections`, so they are classed "unknown" even though nothing was sent. They therefore skip both retry and failover.
- `smtplib.SMTPRecipientsRefused` and `SMTPDataError` include temporary 4xx replies, but all are treated as definitive.
- A bad `Subject` or filename containing CR/LF raises `HeaderParseError` inside `as_string()`. I confirmed it surfaces as `DeliveryOutcomeUnknownException`, although it is a caller error that should be a 4xx at the API.

### BAR-016 (P1, reliability): API availability
`send_plain_email` is `async def` but calls `apply_async` synchronously (`routes.py:44`). I started the app against an unreachable broker and Redis (`probe/p5.py`): the request returned `500 {"message":"Internal server error"}` after 19.2 s, and concurrent requests queued behind it with the same delay. The cause is blocking kombu connect and retry, plus the Redis result-backend subscription that `apply_async` also performs (`celery_app.py:38`). The route's `except AppException` (`routes.py:51`) does not match kombu errors, so the generic handler (`exception_handlers.py:53-58`) returns 500 without logging. Callers get no 503/Retry-After signal, and `/healthz` still says healthy. Publisher confirms are not enabled (Suspected, from the kombu defaults), so a `202` does not prove the broker persisted the message. The decision to report acceptance without a durable record is the gap that BAR-022 (state) and the outbox issue address.

### BAR-017 and BAR-018 (P2): configuration and coupling
- `broker_host` defaults to the string `"amqp://"` (`celery_app.py:21`), which yields `amqp://guest:guest@amqp://:5672`. I printed the resulting URL. User and password are not percent-encoded. `BROKER_URL`, `RESULT_BACKEND` and `Config.result_backend` are documented but unused. The result backend is a Redis URL with Sentinel `master_name` options. Compose Redis has no auth or Sentinel, yet the URL carries a username and password (Suspected to fail against compose Redis; not run). `visibility_timeout` is a Redis and SQS option and does nothing on AMQP. `task_protocol = 1` is legacy.
- Worker registration depends on importing the API (BAR-018). A worker image therefore needs every API dependency, and API start-up side effects (exporter object, Sentry, loguru sinks) run in the worker. `mail_analytics_task` is not registered. Mailchimp is wired nowhere.

### BAR-019 (P1, bug): production logging
Outside development `fmt` is a JSON-looking string containing literal `{` characters (`logger.py:88-90`). loguru formats it with `str.format_map`, so every emit on the stdout sinks fails with `KeyError: '"time"'`. I ran `ENV=production` with a one-line script and got "Logging error in Loguru Handler" for each of the 3 sinks that matched. The default loguru stderr handler is still installed, so unstructured text still appears. The structured logs the code claims to produce never reach stdout. In addition, each sink uses `level=` as a threshold, so one message is written to every sink at or below its level (up to 6 copies in development files). The tests only assert the sink name (`tests/test_logger.py`).

### BAR-020 (P2): lifecycle defects
`FastAPI(on_teardown=[...])` is not a FastAPI parameter (the signature has `on_shutdown`). I confirmed this by inspecting `FastAPI.__init__`. The argument lands in `**extra`, so `_exporter.stop()` and `SmtpServer().logout()` never run. `@logger.catch` above `@router.post` wraps the already-registered function, so it never executes. `middleware.py:26` builds `SentryAsgiMiddleware` into a local variable that is never used, after a second `sentry_sdk.init`. The request id is always a new UUID (`:36`), so a caller's correlation id is lost.

### BAR-021 to BAR-023 (P1): contract, state, transport
The response carries no identifier, so a caller cannot ask "what happened to my request?". There is no accepted idempotency or correlation header. Error bodies are an ad hoc `{status, message, data}`: validation failures return 400 with Pydantic v1 error-type mapping (`exception_handlers.py:16`), not a stable machine-readable code. The only way into the system other than REST is to publish a Celery-protocol message by hand (task name `mail_sending_task`, kwargs `data` and `request_id`), which ties every producer to Celery internals and to this repo's task names (`celery_app.py:50-63`). Nothing is persisted, so none of the CONTEXT.md states (dispatch, attempt, failure, unknown outcome) can be observed after the fact, and nothing is published back to the caller.

### BAR-024 (P2): provider model
`mailer.py:25-32` picks SMTP then SendGrid by an `if`. Adding a provider means editing that function and `app/services/mail/__init__.py`. The `EmailProvider` Protocol and `EmailService` ABC are good seams, but there is no registry or per-provider configuration. `MAIL_API_TOKEN`/`MAIL_API_URL` are shared, so Mailchimp and SendGrid could not both be configured. There is no health check, circuit breaker or secret rotation, and every provider is a process-wide singleton built at import time (the argument defaults call `get_config()` at definition time). The Mailchimp constructor pings the API, which would fail construction if the network is down.

### BAR-025 to BAR-028: missing mail-domain capabilities
No webhook route, signature verification (SendGrid Signed Event Webhook, SES SNS signatures), suppression store, unsubscribe headers or templating code exists. Today every send is "fire and hope". Bounces and complaints from SendGrid or SMTP DSNs go nowhere. Sending again to hard-bounced or complaining addresses damages sender reputation, and when the SMTP path times out the unknown outcome can never be resolved.

### BAR-029 to BAR-031: scale and reputation
- Celery `rate_limit` is "10/s" per worker instance, not a global or per-tenant limit. With N workers the aggregate rate is 10N/s. It also cannot isolate one tenant's burst from another.
- The full message and attachments are serialised into the broker, and task results are written to Redis for every send. `worker_max_tasks_per_child=100` recycles children and drops the SMTP connection every 100 mails. A message with many recipients is one send, so there is no batching or splitting by provider limits.

### BAR-032 (P2): metrics and health
The `Counter`s in `app/metrics.py` are process-local. Workers increment them, the API serves them. Only the exporter-derived metrics are meaningful. The exporter object is created at import time in every API process and consumes the Celery event stream from a daemon thread, so N replicas each rebuild the same metrics. `/healthz` returns a constant. The system has no readiness check for the broker, the result backend or the providers.

### BAR-033 (P1, ops): container
`RUN pipenv lock -r > requirements.txt` fails on current pipenv (I ran it with 2026.8.0 and it printed usage). Even where it works it would re-lock the unpinned Pipfile and ignore `Pipfile.lock`, so builds are not reproducible. `python:3.10.5-slim` is from June 2022, and 3.10 is end-of-life on 2026-10-31. `asgi_server.py` sets `reload = ENV == "development"` with a default of `"development"`, so an image with no `ENV` runs with the reloader. No `HEALTHCHECK`, no multi-stage build, no separate worker command. Compose pins RabbitMQ 3.7.9 and uses `:latest` for Flower and MailHog.

### BAR-034 (P1, CI)
- `make lint` runs `pylint app`, which exits 4. `# pylint: disable=broad-except` is the old name, and pylint 4 reports `W0718` anyway (4 hits). `tests.yml` runs only on `workflow_run` of "Lint" with `conclusion == 'success'`, and `docker.yml` runs only after "Tests". Today the chain stops at Lint.
- `workflow_run` workflows check out the default branch's code unless `ref` is set. `tests.yml` has no `ref`, so even when it runs it tests `develop`, not the PR commit. `lint.yml` triggers on `push` only.
- `slack.yml` listens for a workflow named "Test" (the workflow is "Tests"). `sentry.yml` listens for "Build" (none exists) and also uses `pipenv lock -r`.
- `dangerci.yml` runs yarn and `dangerfile.ts` checks `package.json` and `yarn.lock` in a repo that has neither. Only the assignee and PR-size rules apply.
- `codeql.yml` uses `codeql-action@v2` and analyses only `main`. `bitbucket_sync.yml` and `gitlab_sync.yml` send repository tokens to an unpinned third-party action (`wangchucheng/git-repo-sync@v0.1.0`).
- CI installs with `pipenv requirements --dev ... pip install --no-deps`. That merges `default` and `develop`, which pin different celery, kombu, urllib3 and werkzeug versions (BAR-035). Black is not enforced and would reformat 24 files.
- dependabot covers `pip` only (not GitHub Actions or Docker) and lists `dependabot` as assignee.

### BAR-035 (P2): dependency health
- `pip install -r` of the locked default set fails with `ResolutionImpossible`. `httpcore 1.0.7` requires `h11<0.15` but `h11 0.16.0` is locked. `pip check` also flags `watchgod` against `anyio 4.15` and `flask 3.1.3` against `itsdangerous 2.1.2`. CI avoids the error only through `--no-deps`.
- The `develop` section pins older versions than `default`: celery 5.3.4 (vs 5.6.3), kombu 5.3.2, `urllib3 1.26.20` and `werkzeug 3.1.8`. pip-audit on this section reports 11 urllib3 advisories (fixed in 2.8.0) and CVE-2026-102598 for werkzeug (fixed in 3.1.9). The default section has `ecdsa 0.19.2` PYSEC-2026-1325. The `default` set is otherwise current (dependabot is active).
- `Pipfile` pins everything to `*`.
- `gunicorn`, `marshmallow`, `requests` and `pika` (tests only) are declared but unused by `app/`.
- Python 3.10 reaches end of life on 2026-10-31, so the Pipfile, Docker, `.python-version` and CI matrix all need a new target.

### BAR-036 to BAR-038 (P3/P2): debt, tests and docs
- Pydantic 2.13 prints "Valid config keys have changed in V2: schema_extra" at import. `@validator`, `@root_validator(pre=True)`, `.dict()` and `.parse_obj()` are deprecated and removed in Pydantic 3.
- Test reality (see `05-test-strategy.md`). 82 pass and 1 skips, and every provider call is a mock. Authentication is replaced by `dependency_overrides[get_current_auth] = lambda: None` in `tests/__init__.py:22`. There is no test of the real MIME output beyond headers, nor of config validation, the production logger or the broker topology against a real RabbitMQ in CI.
- README mentions `app/constants.py` and `make run-worker`, neither of which exists. `MANIFEST.in` references `app/templates` and `app/static`. A root `.toml` file holds a Black configuration that no tool reads. There is no LICENSE file.
