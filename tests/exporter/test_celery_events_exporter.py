"""Unit tests for Celery event exporter."""

import time
from unittest.mock import patch, MagicMock

import pytest

from app.exporter.celery_events_exporter import CeleryEventExporter
from app.metrics import task_latency_seconds, task_queue_depth


def test_exporter_initialization():
    """Test that exporter initializes correctly."""
    exporter = CeleryEventExporter()
    assert exporter.running is False
    assert exporter.worker_thread is None
    assert len(exporter.pending_tasks) == 0


def test_process_event_task_sent():
    """Test processing task-sent event."""
    exporter = CeleryEventExporter()
    task_id = "test-task-123"
    timestamp = time.time()

    event = {
        "type": "task-sent",
        "uuid": task_id,
        "timestamp": timestamp,
    }

    exporter._process_event(event)

    assert task_id in exporter.pending_tasks
    assert exporter.pending_tasks[task_id]["sent_at"] == timestamp


def test_process_event_task_succeeded():
    """Test processing task-succeeded event and recording latency."""
    exporter = CeleryEventExporter()
    task_id = "test-task-456"
    sent_time = time.time()

    # First, add the task as sent
    exporter.pending_tasks[task_id] = {"sent_at": sent_time}

    # Now process success event with slight delay
    success_time = sent_time + 1.5
    event = {
        "type": "task-succeeded",
        "uuid": task_id,
        "timestamp": success_time,
        "name": "app.tasks.mail_sending_task",
    }

    # Mock the histogram to capture observations
    with patch("app.exporter.celery_events_exporter.task_latency_seconds") as mock_histogram:
        mock_labels = MagicMock()
        mock_histogram.labels.return_value = mock_labels
        exporter._process_event(event)

        # Verify histogram was updated with correct latency
        mock_histogram.labels.assert_called_once()
        call_kwargs = mock_histogram.labels.call_args[1]
        assert call_kwargs["task_name"] == "app.tasks.mail_sending_task"
        assert call_kwargs["state"] == "succeeded"
        mock_labels.observe.assert_called_once()
        latency = mock_labels.observe.call_args[0][0]
        assert abs(latency - 1.5) < 0.1  # Allow small rounding difference

    # Task should be removed from pending after completion
    assert task_id not in exporter.pending_tasks


def test_process_event_task_failed():
    """Test processing task-failed event."""
    exporter = CeleryEventExporter()
    task_id = "test-task-789"
    sent_time = time.time()

    # Add task as sent
    exporter.pending_tasks[task_id] = {"sent_at": sent_time}

    # Process failure event
    failed_time = sent_time + 0.5
    event = {
        "type": "task-failed",
        "uuid": task_id,
        "timestamp": failed_time,
        "name": "app.tasks.mail_sending_task",
    }

    with patch("app.exporter.celery_events_exporter.task_latency_seconds") as mock_histogram:
        mock_labels = MagicMock()
        mock_histogram.labels.return_value = mock_labels
        exporter._process_event(event)

        mock_histogram.labels.assert_called_once()
        call_kwargs = mock_histogram.labels.call_args[1]
        assert call_kwargs["state"] == "failed"

    # Task should be removed from pending
    assert task_id not in exporter.pending_tasks


def test_process_event_updates_queue_depth():
    """Test that queue depth gauge is updated."""
    exporter = CeleryEventExporter()

    # Add multiple tasks
    for i in range(3):
        task_id = f"task-{i}"
        event = {"type": "task-sent", "uuid": task_id, "timestamp": time.time()}
        with patch("app.exporter.celery_events_exporter.task_queue_depth") as mock_gauge:
            exporter._process_event(event)
            # Queue depth should be set after each event
            mock_gauge.set.assert_called()


def test_queue_backpressure():
    """Test that event queue handles backpressure gracefully."""
    exporter = CeleryEventExporter(max_queue_size=2)
    
    # Add events until queue is full
    for i in range(5):
        event = {"type": "task-sent", "uuid": f"task-{i}", "timestamp": time.time()}
        exporter._handle_event(event)
    
    # Queue should handle backpressure without raising
    assert exporter.event_queue.qsize() <= exporter.max_queue_size


def test_pending_tasks_memory_cleanup():
    """Test that old pending tasks are cleaned up."""
    exporter = CeleryEventExporter()
    
    # Simulate old task (older than 1 hour)
    old_task_id = "old-task"
    one_hour_ago = time.time() - 3700  # 1 hour + 100 seconds
    exporter.pending_tasks[old_task_id] = {"sent_at": one_hour_ago}
    
    # Simulate new task
    new_task_id = "new-task"
    exporter.pending_tasks[new_task_id] = {"sent_at": time.time()}
    
    # Force cleanup by filling pending_tasks beyond limit
    for i in range(exporter.max_pending_tasks + 100):
        task_id = f"temp-task-{i}"
        exporter.pending_tasks[task_id] = {"sent_at": time.time()}
    
    # Process an event to trigger cleanup
    event = {"type": "task-sent", "uuid": "trigger-cleanup", "timestamp": time.time()}
    exporter._process_event(event)
    
    # Old task should be cleaned up, new task should remain
    assert old_task_id not in exporter.pending_tasks
    assert new_task_id in exporter.pending_tasks
