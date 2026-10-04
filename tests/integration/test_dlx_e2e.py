import os
import time
import json
import subprocess
from http.client import HTTPConnection

import pika


BROKER_HOST = os.environ.get("BROKER_HOST", "localhost")
BROKER_PORT = int(os.environ.get("BROKER_PORT", "5672"))
BROKER_USER = os.environ.get("BROKER_USER", "barua-dlx-test")
BROKER_PASSWORD = os.environ.get("BROKER_PASSWORD", "barua-dlx-test-password")

EXCHANGE = "barua-exchange"
ROUTING_KEY = "barua-routing-key"
QUEUE = "barua-queue"
ERROR_QUEUE = "barua-error-queue"


def wait_for_broker(host, port, timeout=60.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=host,
                    port=port,
                    credentials=pika.PlainCredentials(BROKER_USER, BROKER_PASSWORD),
                    connection_attempts=1,
                    socket_timeout=2,
                )
            )
            connection.close()
            return True
        except pika.exceptions.AMQPConnectionError:
            time.sleep(0.5)
    return False


def configure_broker_user(timeout=60.0):
    base_command = ["docker", "compose", "exec", "-T", "broker", "rabbitmqctl"]
    deadline = time.time() + timeout
    last_error = ""

    while time.time() < deadline:
        result = subprocess.run(
            [*base_command, "add_user", BROKER_USER, BROKER_PASSWORD],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            break

        result = subprocess.run(
            [*base_command, "change_password", BROKER_USER, BROKER_PASSWORD],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            break

        last_error = result.stderr or result.stdout
        time.sleep(0.5)
    else:
        raise RuntimeError(f"Could not configure RabbitMQ test user: {last_error}")

    subprocess.check_call(
        [
            *base_command,
            "set_permissions",
            "-p",
            "/",
            BROKER_USER,
            ".*",
            ".*",
            ".*",
        ]
    )


def wait_for_rabbitmq(timeout=60.0):
    deadline = time.time() + timeout
    last_error = ""

    while time.time() < deadline:
        connection = HTTPConnection(BROKER_HOST, 15672, timeout=2)
        try:
            connection.request("GET", "/api/overview")
            response = connection.getresponse()
            response.read()
            if response.status in (200, 401):
                return
            last_error = f"RabbitMQ management API returned HTTP {response.status}"
        except OSError as error:
            last_error = str(error)
        finally:
            connection.close()
        time.sleep(0.5)

    raise RuntimeError(f"RabbitMQ did not become ready: {last_error}")


def wait_for_message(channel, queue, timeout=10.0, poll_interval=0.1, auto_ack=False):
    deadline = time.monotonic() + timeout
    while True:
        result = channel.basic_get(queue=queue, auto_ack=auto_ack)
        if result[0] is not None:
            return result

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return result
        time.sleep(min(poll_interval, remaining))


def test_dlx_end_to_end():
    """Bring up RabbitMQ via docker-compose, publish a message, reject it and assert it lands in the error queue.

    Requirements: Docker Compose v2 must be available locally. This test starts the broker service using
    `docker compose up -d broker` and stops it at the end using `docker compose stop broker`.
    """
    broker_environment = os.environ.copy()
    subprocess.check_call(
        ["docker", "compose", "up", "-d", "broker"],
        env=broker_environment,
    )

    conn = None
    try:
        wait_for_rabbitmq()
        configure_broker_user()
        assert wait_for_broker(BROKER_HOST, BROKER_PORT), "RabbitMQ did not become available"
        params = pika.ConnectionParameters(
            host=BROKER_HOST,
            port=BROKER_PORT,
            credentials=pika.PlainCredentials(BROKER_USER, BROKER_PASSWORD),
        )
        conn = pika.BlockingConnection(params)
        ch = conn.channel()

        ch.exchange_declare(exchange=EXCHANGE, passive=True)
        ch.queue_declare(queue=QUEUE, passive=True)
        ch.queue_declare(queue=ERROR_QUEUE, passive=True)

        payload = {"hello": "dlx-test"}
        body = json.dumps(payload).encode()

        ch.basic_publish(exchange=EXCHANGE, routing_key=ROUTING_KEY, body=body)
        method_frame, _, _ = ch.basic_get(queue=QUEUE, auto_ack=False)
        assert method_frame is not None, "No message received from primary queue"

        ch.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
        err_method, _, err_body = wait_for_message(
            ch, ERROR_QUEUE, timeout=10.0, auto_ack=True
        )

        assert err_method is not None, "Message did not arrive in error queue"
        assert json.loads(err_body.decode()) == payload
    finally:
        if conn is not None and conn.is_open:
            conn.close()
        subprocess.check_call(["docker", "compose", "stop", "broker"])
