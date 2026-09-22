"""
Queues and Exchanges
"""
import os

from kombu import Queue, Exchange

BARUA_DEFAULT_EXCHANGE_NAME = os.environ.get("BARUA_DEFAULT_EXCHANGE", "barua-exchange")
BARUA_DEFAULT_QUEUE_NAME = os.environ.get("BARUA_DEFAULT_QUEUE", "barua-default-queue")
BARUA_DEFAULT_ROUTING_KEY_NAME = os.environ.get(
    "BARUA_DEFAULT_ROUTING_KEY", "barua-default-routing-key"
)

BARUA_EXCHANGE_NAME = os.environ.get("BARUA_EXCHANGE", "barua-exchange")
BARUA_QUEUE_NAME = os.environ.get("BARUA_QUEUE", "barua-queue")
BARUA_ROUTING_KEY_NAME = os.environ.get("BARUA_ROUTING_KEY", "barua-routing-key")
barua_exchange = Exchange(name=BARUA_EXCHANGE_NAME, type="direct")

BARUA_ERROR_EXCHANGE_NAME = os.environ.get(
    "BARUA_ERROR_EXCHANGE", "barua-error-exchange"
)
BARUA_ERROR_QUEUE_NAME = os.environ.get("BARUA_ERROR_QUEUE", "barua-error-queue")
BARUA_ERROR_ROUTING_KEY_NAME = os.environ.get(
    "BARUA_ERROR_ROUTING_KEY", "barua-error-routing-key"
)
barua_error_exchange = Exchange(name=BARUA_ERROR_EXCHANGE_NAME, type="direct")

BARUA_ANALYTICS_QUEUE_NAME = os.environ.get(
    "BARUA_ANALYTICS_QUEUE", "barua-analytics-queue"
)
BARUA_ANALYTICS_ROUTING_KEY_NAME = os.environ.get(
    "BARUA_ANALYTICS_ROUTING_KEY", "barua-analytics-routing-key"
)
BARUA_ANALYTICS_EXCHANGE_NAME = os.environ.get(
    "BARUA_ANALYTICS_EXCHANGE", "barua-analytics-exchange"
)
barua_analytics_exchange = Exchange(name=BARUA_ANALYTICS_EXCHANGE_NAME, type="direct")

BARUA_DEAD_LETTER_EXCHANGE_NAME = os.environ.get(
    "BARUA_DEAD_LETTER_EXCHANGE", "barua-dead-letter-exchange"
)
BARUA_DEAD_LETTER_ROUTING_KEY_NAME = os.environ.get(
    "BARUA_DEAD_LETTER_ROUTING_KEY", "barua-dead-letter-routing-key"
)
barua_dead_letter_exchange = Exchange(
    name=BARUA_DEAD_LETTER_EXCHANGE_NAME, type="direct"
)

# Dead-letter failed messages to the error exchange so they land in the error queue.
# Using the error exchange/routing key as the dead-letter target keeps the flow simple:
# primary queue -> on TTL/negative-ack -> messages routed to error exchange -> error queue
dead_letter_queue_option = {
    "x-message-ttl": 5000,  # delay until the message is transferred in milliseconds
    "x-dead-letter-exchange": BARUA_ERROR_EXCHANGE_NAME,  # route failed messages to error exchange
    "x-dead-letter-routing-key": BARUA_ERROR_ROUTING_KEY_NAME,
}

barua_queue = Queue(
    name=BARUA_QUEUE_NAME,
    routing_key=BARUA_ROUTING_KEY_NAME,
    exchange=barua_exchange,
    queue_arguments=dead_letter_queue_option,
)

# Error queue should be the final sink and not dead-letter back to itself
barua_error_queue = Queue(
    name=BARUA_ERROR_QUEUE_NAME,
    routing_key=BARUA_ERROR_ROUTING_KEY_NAME,
    exchange=barua_error_exchange,
)

barua_analytics_queue = Queue(
    name=BARUA_ANALYTICS_QUEUE_NAME,
    routing_key=BARUA_ANALYTICS_ROUTING_KEY_NAME,
    exchange=barua_analytics_exchange,
    queue_arguments=dead_letter_queue_option,
)
