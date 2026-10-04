"""Unit tests for the Celery event exporter."""

import time
from unittest.mock import MagicMock, patch

from kombu.exceptions import OperationalError

from app.exporter import celery_events_exporter as exporter_module
from app.exporter.celery_events_exporter import CeleryEventExporter


def test_exporter_initialization():
    exporter = CeleryEventExporter()

    assert not exporter.running
    assert exporter.worker_thread is None
    assert exporter.pending_tasks == {}


def test_handle_event_tracks_sent_task():
    exporter = CeleryEventExporter()
    exporter.running = True
    timestamp = time.time()

    exporter._handle_event(
        {"type": "task-sent", "uuid": "task-1", "timestamp": timestamp}
    )

    assert exporter.pending_tasks["task-1"]["sent_at"] == timestamp


def test_process_success_records_runtime_and_removes_task():
    exporter = CeleryEventExporter()
    exporter._process_event(
        {
            "type": "task-received",
            "uuid": "task-1",
            "name": "mail_sending_task",
            "timestamp": time.time(),
        }
    )
    exporter._process_event(
        {
            "type": "task-started",
            "uuid": "task-1",
            "timestamp": time.time(),
        }
    )

    with patch("app.exporter.celery_events_exporter.task_latency_seconds") as histogram:
        exporter._process_event(
            {
                "type": "task-succeeded",
                "uuid": "task-1",
                "runtime": 0.25,
            }
        )

    histogram.labels.assert_called_once_with(
        task_name="mail_sending_task", state="succeeded"
    )
    histogram.labels.return_value.observe.assert_called_once_with(0.25)
    assert "task-1" not in exporter.pending_tasks


def test_process_failure_uses_started_timestamp():
    exporter = CeleryEventExporter()
    started_at = time.time() - 0.5
    exporter.pending_tasks["task-1"] = {
        "name": "mail_sending_task",
        "sent_at": started_at - 5,
        "started_at": started_at,
    }

    with patch("app.exporter.celery_events_exporter.task_latency_seconds") as histogram:
        exporter._process_event(
            {
                "type": "task-failed",
                "uuid": "task-1",
                "timestamp": started_at + 0.5,
            }
        )

    histogram.labels.assert_called_once_with(
        task_name="mail_sending_task", state="failed"
    )
    histogram.labels.return_value.observe.assert_called_once()
    assert "task-1" not in exporter.pending_tasks


def test_failure_without_start_event_does_not_include_queue_wait():
    exporter = CeleryEventExporter()
    exporter.pending_tasks["task-1"] = {"sent_at": time.time() - 10}

    with patch("app.exporter.celery_events_exporter.task_latency_seconds") as histogram:
        exporter._process_event(
            {
                "type": "task-failed",
                "uuid": "task-1",
                "timestamp": time.time(),
            }
        )

    histogram.labels.assert_not_called()


def test_event_without_sent_event_still_records_completion():
    exporter = CeleryEventExporter()
    started_at = time.time()
    exporter._process_event(
        {"type": "task-started", "uuid": "task-1", "timestamp": started_at}
    )

    with patch("app.exporter.celery_events_exporter.task_latency_seconds") as histogram:
        exporter._process_event(
            {
                "type": "task-succeeded",
                "uuid": "task-1",
                "timestamp": started_at + 0.5,
                "name": "mail_sending_task",
            }
        )

    histogram.labels.return_value.observe.assert_called_once_with(0.5)


def test_pending_task_tracking_is_bounded():
    exporter = CeleryEventExporter(max_pending_tasks=2)
    exporter.pending_tasks = {
        "task-1": {"sent_at": time.time()},
        "task-2": {"sent_at": time.time()},
    }

    exporter._process_event(
        {"type": "task-sent", "uuid": "task-3", "timestamp": time.time()}
    )

    assert len(exporter.pending_tasks) == 2
    assert "task-1" not in exporter.pending_tasks
    assert "task-3" in exporter.pending_tasks


def test_pending_task_ttl_is_enforced_below_capacity():
    exporter = CeleryEventExporter(max_pending_tasks=10, pending_task_ttl=60)
    now = time.time()
    exporter.pending_tasks = {
        "expired": {"sent_at": now - 61},
        "active": {"started_at": now},
    }

    exporter._trim_pending_tasks()

    assert exporter.pending_tasks == {"active": {"started_at": now}}


def test_queue_depth_records_ready_messages_per_queue():
    exporter = CeleryEventExporter()
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    channel.queue_declare.return_value.message_count = 3

    with patch("app.exporter.celery_events_exporter.task_queue_depth") as queue_depth:
        exporter._update_queue_depth(connection)

    queue_names = [queue.name for queue in exporter_module.celery_app.conf.task_queues]
    assert channel.queue_declare.call_count == len(queue_names)
    assert [
        call.kwargs["queue_name"] for call in queue_depth.labels.call_args_list
    ] == queue_names
    queue_depth.labels.return_value.set.assert_called_with(3)
    assert channel.close.call_count == len(queue_names)


def test_event_consumer_retries_after_broker_connection_failure():
    exporter = CeleryEventExporter()
    failed_connection = MagicMock()
    failed_connection.connect.side_effect = OperationalError("broker unavailable")
    failed_connection.connected = False
    connected_connection = MagicMock()
    receiver = MagicMock()
    receiver.capture.side_effect = lambda **kwargs: setattr(exporter, "running", False)

    with (
        patch(
            "app.exporter.celery_events_exporter.celery_app.connection",
            side_effect=[failed_connection, connected_connection],
        ) as connect,
        patch(
            "app.exporter.celery_events_exporter.celery_app.events.Receiver",
            return_value=receiver,
        ),
        patch.object(exporter._stop_event, "wait", return_value=False),
        patch.object(exporter, "_update_queue_depth"),
    ):
        exporter.running = True
        exporter._event_consumer_loop()

    assert connect.call_count == 2
    assert not exporter.running
    assert not exporter._connected.is_set()


def test_stop_signals_receiver_and_joins_thread():
    exporter = CeleryEventExporter()
    exporter.running = True
    exporter._receiver = MagicMock()
    exporter.worker_thread = MagicMock()
    exporter.worker_thread.is_alive.return_value = False

    exporter.stop(timeout=2)

    assert exporter._receiver.should_stop
    exporter.worker_thread.join.assert_called_once_with(timeout=2)
