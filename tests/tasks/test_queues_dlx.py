import json
from pathlib import Path

from app.worker import queues


def test_barua_queue_keeps_deployed_dlx_arguments():
    expected_arguments = {
        "x-message-ttl": 5000,
        "x-dead-letter-exchange": queues.BARUA_DEAD_LETTER_EXCHANGE_NAME,
        "x-dead-letter-routing-key": queues.BARUA_DEAD_LETTER_ROUTING_KEY_NAME,
    }

    assert queues.barua_queue.queue_arguments == expected_arguments
    assert queues.barua_analytics_queue.queue_arguments == expected_arguments
    assert queues.barua_error_queue.queue_arguments in (None, {})


def test_rabbitmq_definitions_match_queue_arguments_and_bind_legacy_dlx():
    definitions_path = Path(__file__).parents[2] / "docker" / "rabbitmq_definitions.json"
    definitions = json.loads(definitions_path.read_text())

    expected_arguments = queues.barua_queue.queue_arguments
    configured_queues = {queue["name"]: queue for queue in definitions["queues"]}
    assert configured_queues[queues.BARUA_QUEUE_NAME]["arguments"] == expected_arguments
    assert configured_queues[queues.BARUA_ERROR_QUEUE_NAME]["arguments"] == {}
    assert (
        configured_queues[queues.BARUA_ANALYTICS_QUEUE_NAME]["arguments"]
        == expected_arguments
    )

    assert {
        "name": queues.BARUA_DEAD_LETTER_EXCHANGE_NAME,
        "vhost": "/",
        "type": "direct",
        "durable": True,
        "auto_delete": False,
        "internal": False,
        "arguments": {},
    } in definitions["exchanges"]
    assert {
        "source": queues.BARUA_DEAD_LETTER_EXCHANGE_NAME,
        "vhost": "/",
        "destination": queues.BARUA_ERROR_QUEUE_NAME,
        "destination_type": "queue",
        "routing_key": queues.BARUA_DEAD_LETTER_ROUTING_KEY_NAME,
        "arguments": {},
    } in definitions["bindings"]
