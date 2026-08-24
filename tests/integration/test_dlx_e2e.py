import os
import time
import json
import subprocess
import socket

import pika


BROKER_HOST = os.environ.get("BROKER_HOST", "localhost")
BROKER_PORT = int(os.environ.get("BROKER_PORT", "5672"))

EXCHANGE = "barua-exchange"
ROUTING_KEY = "barua-routing-key"
QUEUE = "barua-queue"
ERROR_QUEUE = "barua-error-queue"


def wait_for_port(host, port, timeout=30.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def test_dlx_end_to_end():
    """Bring up RabbitMQ via docker-compose, publish a message, reject it and assert it lands in the error queue.

    Requirements: docker-compose must be available locally. This test will start the broker service using
    `docker-compose up -d broker` and stop it at the end using `docker-compose stop broker`.
    """
    # start broker
    subprocess.check_call(["docker-compose", "up", "-d", "broker"])  # may be noop if already running

    assert wait_for_port(BROKER_HOST, BROKER_PORT, timeout=30), "RabbitMQ did not become available"

    params = pika.ConnectionParameters(host=BROKER_HOST, port=BROKER_PORT)

    conn = pika.BlockingConnection(params)
    ch = conn.channel()

    # ensure exchanges/queues exist (definitions.json should have declared them, but declare idempotently)
    ch.exchange_declare(exchange=EXCHANGE, exchange_type='direct', durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_declare(queue=ERROR_QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)

    payload = {"hello": "dlx-test"}
    body = json.dumps(payload).encode()

    # publish to the exchange so it lands on the primary queue
    ch.basic_publish(exchange=EXCHANGE, routing_key=ROUTING_KEY, body=body)

    # get the message from primary queue and reject it (nack without requeue)
    method_frame, header_frame, received_body = ch.basic_get(queue=QUEUE, auto_ack=False)
    assert method_frame is not None, "No message received from primary queue"

    # reject the message (do not requeue) so it will be routed to DLX
    ch.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)

    # allow a short moment for RabbitMQ to move the message to the DLX target
    time.sleep(2)

    # attempt to read from error queue
    err_method, err_header, err_body = ch.basic_get(queue=ERROR_QUEUE, auto_ack=True)

    # cleanup connection
    conn.close()

    # stop broker to clean up (best-effort)
    try:
        subprocess.check_call(["docker-compose", "stop", "broker"])
    except Exception:
        pass

    assert err_method is not None, "Message did not arrive in error queue"

    parsed = json.loads(err_body.decode())
    assert parsed == payload
