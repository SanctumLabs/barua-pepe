import os
from celery import Celery
from kombu import Queue
from app.constants import EMAIL_DEFAULT_EXCHANGE, EMAIL_DEFAULT_QUEUE_NAME, EMAIL_DEFAULT_ROUTING_KEY, EMAIL_EXCHANGE, \
    EMAIL_QUEUE_NAME, EMAIL_ROUTING_KEY, EMAIL_ERROR_EXCHANGE, EMAIL_ERROR_ROUTING_KEY, EMAIL_ERROR_QUEUE_NAME

broker = os.environ.get("BROKER_URL", "amqp://")
result_backend = os.environ.get("RESULT_BACKEND", "rpc://")
result_backend_master = os.environ.get("RESULT_BACKEND_LEADER", "redismaster")

celery_app = Celery("BaruaPepeWorker", broker=broker, backend=result_backend, include=["app.tasks"])

# Task Queues
task_queues = (
    Queue(name=EMAIL_DEFAULT_QUEUE_NAME, routing_key=EMAIL_DEFAULT_ROUTING_KEY, exchange=EMAIL_DEFAULT_EXCHANGE),
    Queue(name=EMAIL_QUEUE_NAME, routing_key=EMAIL_ROUTING_KEY, exchange=EMAIL_EXCHANGE),
    Queue(name=EMAIL_ERROR_QUEUE_NAME, routing_key=EMAIL_ERROR_ROUTING_KEY, exchange=EMAIL_ERROR_EXCHANGE,
          queue_arguments={
              'x-message-ttl': 5000,  # delay until the message is transferred in milliseconds
              'x-dead-letter-exchange': EMAIL_ERROR_EXCHANGE,  # Exchange used to transfer the message from A to B.
              'x-dead-letter-routing-key': EMAIL_ERROR_ROUTING_KEY
              # Name of the queue we want the message transferred to.
          })
)

# Task Routes
task_routes = {
    "mail_sending_task": dict(
        queue=EMAIL_QUEUE_NAME
    ),
    "mail_error_task": dict(
        queue=EMAIL_ERROR_QUEUE_NAME
    )
}

result_backend_transport_options = {
    'master_name': result_backend_master,
    'retry_policy': {
        'timeout': 5.0
    }
}

# Set task routes and queues

celery_app.conf.task_routes = task_routes
celery_app.conf.task_default_exchange = EMAIL_DEFAULT_EXCHANGE
celery_app.conf.task_default_routing_key = EMAIL_DEFAULT_ROUTING_KEY
celery_app.conf.task_default_queue = EMAIL_DEFAULT_QUEUE_NAME
celery_app.conf.result_backend_transport_options = result_backend_transport_options
celery_app.conf.task_queues = task_queues
celery_app.conf.task_protocol = 1
