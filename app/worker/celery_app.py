"""
Celery application
"""
import os
from celery import Celery
from .queues import (
    barua_queue,
    barua_analytics_queue,
    barua_error_queue,
    BARUA_QUEUE_NAME,
    BARUA_ROUTING_KEY_NAME,
    BARUA_ERROR_QUEUE_NAME,
    BARUA_ERROR_ROUTING_KEY_NAME,
    BARUA_ANALYTICS_QUEUE_NAME,
    BARUA_ANALYTICS_ROUTING_KEY_NAME,
    BARUA_DEFAULT_EXCHANGE_NAME,
    BARUA_DEFAULT_QUEUE_NAME,
    BARUA_DEFAULT_ROUTING_KEY_NAME,
)

broker_host = os.environ.get("BROKER_HOST", "amqp://")
broker_port = os.environ.get("BROKER_PORT", "5672")
broker_username = os.environ.get("BROKER_USER", "guest")
broker_password = os.environ.get("BROKER_PASSWORD", "guest")

broker_transport_options = {
    "visibility_timeout": 43200,
}

broker_url = f"amqp://{broker_username}:{broker_password}@{broker_host}:{broker_port}"

backend_host = os.environ.get("RESULT_BACKEND_HOST", "localhost")
backend_port = os.environ.get("RESULT_BACKEND_PORT", "6379")
backend_username = os.environ.get("RESULT_BACKEND_USERNAME", "barua-pepe-user")
backend_password = os.environ.get("RESULT_BACKEND_PASSWORD", "barua-pepe-password")
backend_db = os.environ.get("RESULT_BACKEND_DB", "0")

backend_url = f"redis://{backend_username}:{backend_password}@{backend_host}:{backend_port}/{backend_db}"

backend_master = os.environ.get("RESULT_BACKEND_LEADER", "redismaster")
backend_transport_options = {
    "master_name": backend_master,
    "retry_policy": {"timeout": 5.0},
}

# Task Queues
task_queues = (barua_queue, barua_analytics_queue, barua_error_queue)

# Task Routes
task_routes = {
    "mail_sending_task": dict(
        queue=BARUA_QUEUE_NAME, routing_key=BARUA_ROUTING_KEY_NAME
    ),
    "mail_error_task": dict(
        queue=BARUA_ERROR_QUEUE_NAME, routing_key=BARUA_ERROR_ROUTING_KEY_NAME
    ),
    "mail_analytics_task": dict(
        queue=BARUA_ANALYTICS_QUEUE_NAME, routing_key=BARUA_ANALYTICS_ROUTING_KEY_NAME
    ),
}

celery_app = Celery(
    "BaruaPepeWorker", broker=broker_url, backend=backend_url, include=["app.tasks"]
)

# Set task routes and queues

celery_app.conf.task_routes = task_routes
celery_app.conf.task_default_exchange = BARUA_DEFAULT_EXCHANGE_NAME
celery_app.conf.task_default_routing_key = BARUA_DEFAULT_ROUTING_KEY_NAME
celery_app.conf.task_default_queue = BARUA_DEFAULT_QUEUE_NAME
celery_app.conf.backend_transport_options = backend_transport_options
celery_app.conf.broker_transport_options = broker_transport_options
celery_app.conf.task_queues = task_queues
# Reliability and retrying defaults
celery_app.conf.task_protocol = 1
# Acknowledge tasks after the worker has executed them so they are re-queued on worker failure
celery_app.conf.task_acks_late = True
# Ensure tasks are rejected if the worker is lost
celery_app.conf.worker_disable_rate_limits = False
celery_app.conf.task_reject_on_worker_lost = True
# Default retry delay (seconds) if a task does not override it
celery_app.conf.task_default_retry_delay = 30
# Optionally declare annotations for specific tasks (can be augmented later)
celery_app.conf.task_annotations = {
    "mail_sending_task": {
        "rate_limit": "10/s",
        "soft_time_limit": 60,
        "time_limit": 120,
        "acks_late": True,
    },
    "mail_error_task": {"rate_limit": "2/s", "soft_time_limit": 120, "time_limit": 300},
}

# Worker tuning for stability
celery_app.conf.worker_max_tasks_per_child = int(os.environ.get("CELERY_MAX_TASKS_PER_CHILD", "100"))
celery_app.conf.worker_prefetch_multiplier = int(os.environ.get("CELERY_PREFETCH_MULTIPLIER", "1"))
celery_app.conf.broker_heartbeat = int(os.environ.get("CELERY_BROKER_HEARTBEAT", "30"))
celery_app.conf.broker_connection_retry = True

# Enable event sending to support monitoring tools (flower, prometheus exporters)
celery_app.conf.worker_send_task_events = True
celery_app.conf.send_events = True

