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
celery_app.conf.task_protocol = 1
