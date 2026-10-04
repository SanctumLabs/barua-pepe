"""Unit tests for the Celery event exporter."""

import time
from unittest.mock import MagicMock, patch

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

    with patch(
        "app.exporter.celery_events_exporter.task_latency_seconds"
    ) as histogram:
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
    exporter.pending_tasks["task-1"] = {"started_at": started_at}

    with patch(
        "app.exporter.celery_events_exporter.task_latency_seconds"
    ) as histogram:
        exporter._process_event(
            {
                "type": "task-failed",
                "uuid": "task-1",
                "name": "mail_sending_task",
                "timestamp": started_at + 0.5,
            }
        )

    histogram.labels.assert_called_once_with(
        task_name="mail_sending_task", state="failed"
    )
    histogram.labels.return_value.observe.assert_called_once()
    assert "task-1" not in exporter.pending_tasks


def test_event_without_sent_event_still_records_completion():
    exporter = CeleryEventExporter()
    exporter._process_event(
        {"type": "task-started", "uuid": "task-1", "timestamp": 10.0}
    )

    with patch(
        "app.exporter.celery_events_exporter.task_latency_seconds"
    ) as histogram:
        exporter._process_event(
            {
                "type": "task-succeeded",
                "uuid": "task-1",
                "timestamp": 10.5,
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


def test_stop_signals_receiver_and_joins_thread():
    exporter = CeleryEventExporter()
    exporter.running = True
    exporter._receiver = MagicMock()
    exporter.worker_thread = MagicMock()
    exporter.worker_thread.is_alive.return_value = False

    exporter.stop(timeout=2)

    assert exporter._receiver.should_stop
    exporter.worker_thread.join.assert_called_once_with(timeout=2)
