> **Status: Proposed. Discovery output dated 2026-10-07; not accepted architecture.** Describes the code as inspected on that date and a proposal for its replacement. Decisions are tracked in the ADR index and open-question log.

# barua-pepe: as-is design

Inspected: `barua-pepe`, branch `develop` @ `4300df4` (2026-10-07; the working copy is on `claude/cool-hopper-zote46`, which has no diff against `develop`). 229 commits, 2026-06 to 2026-10: 86 by dependabot, 143 by two human accounts. About 4.2k lines of Python (`app/` ~2.2k, `tests/` ~2.0k). No open issues or PRs. Four closed issues (#841-#844, the Oct 2026 architecture work, all merged) and about 100 merged PRs, mostly dependabot.

## 1. What it is

A small FastAPI service with one business endpoint, `POST /api/v1/baruapepe/sendmail`. It accepts an email request, validates it with Pydantic, publishes a Celery task onto RabbitMQ and returns `202`. A separate Celery worker process picks the task up and submits the mail to SMTP first, with SendGrid as a fallback only when SMTP explicitly rejects it. No state is persisted anywhere: there is no database, no message id and no delivery status.

## 2. Tech stack and versions

| Concern | Choice | Source |
|---|---|---|
| Language | Python 3.10 (`.python-version`, Pipfile `python_version = "3.10"`, Docker `python:3.10.5-slim`). 3.10 reaches EOL on 2026-10-31. | `Pipfile:37`, `Dockerfile:1` |
| Web | FastAPI 0.142.2, Starlette 1.7.0, uvicorn 0.54.0 (`gunicorn` is listed but unused) | `Pipfile.lock` |
| Validation | Pydantic 2.13.5 using v1-style APIs (`validator`, `root_validator`, `.dict()`, `.parse_obj()`) | `app/domain/entities/*` |
| Queue | Celery 5.6.3 in `default`; `develop` pins 5.3.4. RabbitMQ over AMQP. Redis is the result backend. | `app/worker/celery_app.py` |
| Providers | `smtplib` (stdlib), `sendgrid` 6.12.5, `mailchimp-transactional` 1.4.1 | `app/services/mail/` |
| Logging | loguru 0.7.3, sentry-sdk 2.71 | `app/logger.py` |
| Metrics | prometheus-client; a Celery event exporter runs in the API process | `app/metrics.py`, `app/exporter/` |
| Packaging | Pipenv (`Pipfile` all `"*"`, `Pipfile.lock` 306 KB) | |
| CI | GitHub Actions: lint, tests, docker, codeql, danger, integration-dlx, integration-exporter, release (semantic-release), sentry, slack, and mirrors to Bitbucket and GitLab | `.github/workflows/` |

## 3. Layout and layering

```
asgi_server.py            uvicorn.run("app:app", reload = (ENV == "development"))
app/__init__.py           FastAPI app, startup/teardown, router wiring; also starts the Celery event exporter
app/config.py             pydantic-settings Config, validate_production_settings(), get_config()
app/api/mailer/           POST /sendmail route + DTOs (aliases from/to/cc/bcc)
app/api/monitoring/       GET /healthz (static), GET /metrics (Prometheus)
app/application/          dispatch_email(request, dispatcher, request_id), a Protocol seam added Oct 2026
app/infra/adapters/       CeleryEmailDispatcher (mail_sending_task.apply_async)
app/infra/{handlers,middleware}/  exception handlers; request-id/log/security-header middleware
app/domain/entities/      EmailRequest, EmailSender, EmailRecipient, EmailAttachment (Pydantic models)
app/services/auth/        HTTP Basic, one shared username/password from env
app/services/mail/        EmailService ABC; SmtpServer, SendGridEmailService, MailChimpEmailService;
                          delivery_policy.deliver_email (primary/fallback); mailer.send_plain_mail (hard-coded selection)
app/tasks/                mail_sending_task, mail_error_task (+ stub mail_error_callback_task), mail_analytics_task
app/worker/               celery_app (config), queues (kombu exchanges/queues)
app/exporter/             CeleryEventExporter: consumes Celery events, publishes metrics, polls queue depth
tests/                    unit + API + exporter + 1 docker-compose integration test + a locust file
```

The layering is hexagonal in intent and only partly in practice:
- `application/email_dispatch.py` and `domain/` are clean seams. The domain model imports nothing from infrastructure.
- `app/__init__.py` imports the exporter, services and API all together. `app.worker.celery_app` lists `include=["app.tasks"]`, and `app/tasks/__init__.py` is empty. The worker therefore only registers its tasks because importing the `app` package pulls in the whole FastAPI app, which imports the Celery adapter and then `mail_sending_task`. I verified this: with the `app` package imported, `celery_app.tasks` contains `mail_sending_task`, `mail_error_task` and `mail_error_callback_task`, and does not contain `mail_analytics_task` (BAR-018).
- Provider selection is hard-coded in `app/services/mail/mailer.py:25-32`. There is no registry or plug-in mechanism.

## 4. Main flows

### 4.1 Send (happy path)
1. The client calls `POST /api/v1/baruapepe/sendmail` with HTTP Basic auth (`app/__init__.py:61-62` applies `get_current_auth` to the router). The auth check is a constant-time compare against a single global `USERNAME`/`PASSWORD`, which default to `barua-pepe-user`/`barua-pepe-password` (`app/config.py:63-64`).
2. `request_context_middleware` generates a server-side UUID `request_id`. It ignores any inbound correlation header. It also binds a loguru logger and logs the full URL (`middleware.py:36-55`).
3. `EmailRequestDto` is validated: `from`, `to`, `cc`, `bcc`, `subject`, `message` and `attachments[{content, filename, type}]`. The only rules are: non-empty subject, message and recipients, `EmailStr` addresses, and non-empty attachment content and filename. There are no size limits, no base64 or MIME checks and no CR/LF checks.
4. The route calls `dispatch_email` synchronously inside an `async def` handler (`routes.py:44`). That reaches `mail_sending_task.apply_async(kwargs={data: <EmailRequest.dict()>, request_id})` (`celery_email_dispatcher.py:13-18`). The whole message, including base64 attachments, becomes the broker payload.
5. The route returns `202 {"status":202,"message":"Email request accepted for processing","data":null}`. There is no message id and no way to query status afterwards (`routes.py:46-50`).
6. The worker (`mail_sending_task`, `acks_late`, `max_retries=3`, `rate_limit=10/s` per worker instance, `soft_time_limit=60`, `time_limit=120`) rebuilds the `EmailRequest`, calls `send_plain_mail`, and that calls `deliver_email(primary=SmtpServer, fallback=SendGridEmailService)`, or SendGrid alone when `MAIL_SMTP_ENABLED=false`.
7. The result dict `{success, message}` goes to the result backend. The message string contains the sender and recipient addresses (`smtp_proxy.py:131-134`).

### 4.2 Failure handling
- Validation failure in the worker: logged, a `mail_error_task` is enqueued, and the task re-raises (`mail_sending_task.py:36-42`).
- `DeliveryRejectedException` from both providers becomes `EmailSendingException`. This falls into the generic `except Exception` branch, which retries with 30s, 60s and 120s backoff and calls `mail_error_task` at the last attempt (`:58-71`).
- `DeliveryOutcomeUnknownException` (timeouts, 5xx, connection loss) is not retried and not failed over. `mail_error_task` is enqueued and the exception re-raised (`:50-56`).
- `mail_error_task` increments a counter and logs the recipient count. The payload is never stored and nothing replays it (`mail_error_task.py:24-38`).
- RabbitMQ topology: `barua-queue` and `barua-analytics-queue` are declared with `x-message-ttl: 5000` and a dead-letter exchange routed to `barua-error-queue` (`app/worker/queues.py:51-62`, `docker/rabbitmq_definitions.json`). A message that waits longer than 5 seconds in the primary queue is dead-lettered. The test `tests/tasks/test_queues_dlx.py` pins this deliberately as "deployed" behaviour (commit `963bf07`).

### 4.3 Observability
- `/healthz` returns a static 200 and never touches the broker or the SMTP server.
- `/metrics` serves the API process registry. The send counters (`barua_email_send_*`, `barua_email_error_tasks_total`) are incremented inside Celery worker processes (`mail_sending_task.py:40,45,54,63`, `mail_error_task.py:38`), so the API's `/metrics` never sees them. The only exporter metrics that work are task latency (derived from Celery events), pending-task count and queue depth (`app/exporter/celery_events_exporter.py`).
- Sentry is initialised twice (`logger.py:27-38`, `middleware.py:19-24`).
- The loguru sinks are broken in production (BAR-019).

## 5. Data model
There is none. The only durable state is RabbitMQ messages and, for a day or so, task results in the Redis or RPC result backend. There are no schemas, no migrations, no message table, no suppression store and no tenant records.

## 6. Configuration
Pydantic `Config` (`app/config.py`) is populated from environment variables plus `.env` (`load_dotenv()`). Celery and queue names are read directly from `os.environ` in `app/worker/*.py`, which bypasses `Config`.
- `ENV` is read by `logger.py` and `asgi_server.py`. `Config.environment` reads `ENVIRONMENT`. These are different variables, so the production validation never runs when only `ENV=production` is set (BAR-002).
- Broker URL is built as `amqp://{user}:{pass}@{host}:{port}` with the default host `"amqp://"`, which produces an invalid URL when `BROKER_HOST` is unset (`celery_app.py:21-30`). The credentials are not URL-escaped. `.env.example` documents `BROKER_URL` and `RESULT_BACKEND`, but nothing reads them.
- The result backend is `redis://user:pass@host:port/db`, combined with Sentinel-style `master_name` transport options. The compose Redis has no auth or Sentinel (`celery_app.py:38-44`, `docker-compose.yml:15`).
- One `MAIL_API_TOKEN` is shared by every API provider.

## 7. Deployment and CI
- Dockerfile: `python:3.10.5-slim`, `COPY . .`, `RUN pipenv lock -r > requirements.txt`, `pip install -r requirements.txt`, then the non-root user, `CMD python asgi_server.py`. `pipenv lock -r` no longer exists. I ran it with pipenv 2026.8.0 and it prints a usage error, so the image cannot be built. It would also re-lock from the unpinned Pipfile and ignore `Pipfile.lock`. With `ENV` unset the process starts with uvicorn `reload=True`. There is no HEALTHCHECK and no worker entrypoint.
- `docker-compose.yml`: RabbitMQ 3.7.9 (EOL since 2019) with `guest` credentials, Redis 7.0.2, `mher/flower:latest` with no auth, `mailhog:latest`. The API and worker themselves are not services in compose.
- CI: see BAR-034. In short, `Lint` runs `pylint app` and currently exits 4. `Tests` and `Docker` are chained behind it through `workflow_run`.
- Releases: semantic-release (`npx`) from `main`. `develop` is configured as a prerelease branch, but the release workflow only triggers on `main`.

## 8. Implemented vs stubbed or documented

| Capability | Status |
|---|---|
| Accept request, validate, enqueue, return 202 | Implemented |
| SMTP provider | Implemented, but attachments are corrupted, HTML is sent as plain text, auth runs only in the API process, there are no timeouts, and partial refusals are reported as success (BAR-009..013) |
| SendGrid provider | Implemented (To/CC/BCC, HTML or text detected by substring, attachments) |
| Mailchimp Transactional provider | Present and exported, never wired in. Attachment shape is wrong (`filename` vs `name`). It also treats any 200 as accepted, but Mailchimp reports per-recipient `rejected` in the body. Dead code. |
| Fallback policy (SMTP to SendGrid only on explicit rejection) | Implemented, unit-tested with mocks only |
| Retries/backoff | Implemented in the task (Celery `retry`) |
| DLQ | Topology present. The consumer logs and drops. It does not replay, store or inspect. |
| Analytics queue and `mail_analytics_task` | Queue and task exist. Nothing publishes to it, the task is not registered in the worker, and it does the same thing as the send task. |
| `mail_error_callback_task` | Empty stub (docstring says "event callbacks"). |
| Webhooks (bounce, complaint, delivery, open, click) | Absent. No code, README or CONTEXT mention. |
| Delivery state machine / status API / outbound events | Absent. CONTEXT.md defines dispatch, attempt, failure and unknown outcome, but nothing persists or reports them. |
| Suppression list, unsubscribe (RFC 8058), List-Unsubscribe | Absent |
| Templating, localisation, plain-text alternative | Absent. `jinja2` is in the lock only as a transitive dependency of other packages. |
| Attachment limits, MIME checks, AV, storage | Absent |
| Idempotency keys | Absent |
| Per-tenant limits, warm-up, IP pools, batching | Absent. The only throttle is a per-worker-instance Celery `rate_limit`. |
| SPF/DKIM/DMARC | Not addressed anywhere. They depend on the relay or provider, and the README says nothing. |
| Multi-tenancy, authz | Absent. One shared Basic credential. |
| DB and migrations | Absent |
| Readiness probe, graceful shutdown | Absent (`on_teardown` is not a FastAPI parameter, so teardown never runs, BAR-020) |
| Documented `app/constants.py`, `make run-worker`, `app/templates`, `app/static` | Referenced in README or MANIFEST but not present |

## 9. History and churn (what the git log says)
- All 229 commits fall between 2026-06-04 and 2026-10-07. 86 are dependabot bumps. Most of the Pipfile.lock churn (89 touches) is Celery 5.3.4 to 5.6.3 re-bumped repeatedly, because the `develop` section keeps pinning 5.3.4 via `celery[pytest]`.
- Human work is concentrated in `mail_sending_task.py` (13 touches), the DLX integration workflow (12), `mail_error_task.py` (11), `routes.py` (9) and `app/domain/send_email.py` (8, deleted in `bb3524f`). It follows a pattern of "CI repairs and DLQ plumbing" (Aug 2026) and then "architecture seams" (Oct 2026: canonical contract, dispatch seam, delivery policy, SMTP envelope fix).
- The Oct 2026 work (#841-#844) did the right thing structurally. It defined `EmailRequest`, `dispatch_email` and `deliver_email`, and fixed the CC/BCC envelope. It left the pipeline's reliability, state and security gaps untouched, and tests exercise only mocks.
- Abandoned or dead: Mailchimp provider, analytics queue/task, `mail_error_callback_task`, `TaskException`, `app/templates`/`app/static` in `MANIFEST.in`, the unused `BROKER_URL`/`RESULT_BACKEND`/`Config.result_backend` settings, `asgi_app` in `middleware.py:26`, the root `.toml` (a stray Black config that Black never reads), and the `gunicorn`/`marshmallow`/`requests` dependencies.

## 10. Tests and tools run

| Command | Result |
|---|---|
| `pytest --ignore=tests/integration` (Python 3.11 venv, locked default deps with `--no-deps`, since the lock does not resolve) | **82 passed, 1 skipped**, about 3 s, coverage 82% (`config.py` 70%, `auth_service.py` 58%, `smtp_proxy.py` 62%, `mailchimp_email_service.py` 28%) |
| `pytest tests/integration` | **1 failed** (`test_dlx_e2e`): needs `docker compose up broker`, and Docker is unavailable in this sandbox. Not a code defect. |
| `pylint app` | 9.96/10 but **exit code 4**: four `W0718 broad-exception-caught` on lines that carry the old `# pylint: disable=broad-except` name. `make lint` fails, which fails the Lint workflow. |
| `black --check app` | 24 of 50 files would be reformatted. The line-length is not configured (the `.toml` file is never read), so the default 88 is used, while the Makefile and `.pylintrc` say 120. |
| `pipenv lock -r` | Removed upstream; prints usage. The Dockerfile and `sentry.yml` depend on it. |
| `pip install` of the locked default set | Fails with `ResolutionImpossible`. `httpcore==1.0.7` needs `h11<0.15` but `h11==0.16.0` is locked. `pip check` also reports `watchgod` vs `anyio 4.15`. |
| `pip-audit` on the locked sets | default: `ecdsa 0.19.2` PYSEC-2026-1325 (no fixed version listed). develop: `urllib3 1.26.20` (11 advisories, fixed in 2.8.0), `werkzeug 3.1.8` (CVE-2026-102598, fixed in 3.1.9). |
