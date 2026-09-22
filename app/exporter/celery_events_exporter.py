"""Celery event stream consumer and Prometheus exporter."""

import logging
import threading
import time
from collections import defaultdict
from queue import Queue, Empty
from typing import Dict, Optional

from app.logger import bind_request_context
from app.metrics import (
    task_latency_seconds,
    task_queue_depth,
    event_processing_latency_ms,
)
from app.worker.celery_app import app as celery_app

logger = logging.getLogger(__name__)


class CeleryEventExporter:
    """
    Consumes Celery task events via the event stream and updates Prometheus metrics.

    Tracks:
    - Task execution latency (sent → succeeded/failed)
    - Task queue depth (pending task count)
    - Event processing latency

    Runs in a background thread to avoid blocking the main app.
    """

    def __init__(self, max_queue_size: int = 10000):
        self.max_queue_size = max_queue_size
        self.event_queue: Queue = Queue(maxsize=max_queue_size)
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

        # Track task state for latency calculation: {task_id: {'sent_at': timestamp}}
        self.pending_tasks: Dict[str, dict] = defaultdict(dict)
        self.max_pending_tasks = 100000  # Memory safety limit

    def start(self) -> None:
        """Start the event consumer thread."""
        if self.running:
            logger.warning("Event exporter already running")
            return

        self.running = True
        self.worker_thread = threading.Thread(
            target=self._event_consumer_loop, daemon=True, name="celery-events-exporter"
        )
        self.worker_thread.start()
        logger.info("Celery event exporter started")

    def stop(self, timeout: int = 5) -> None:
        """Stop the event consumer thread and drain pending events."""
        if not self.running:
            return

        self.running = False
        # Drain queue before stopping to process final events
        try:
            while not self.event_queue.empty():
                try:
                    event = self.event_queue.get_nowait()
                    self._process_event(event)
                except Empty:
                    break
        except Exception as e:
            logger.error("Error draining event queue", exc_info=e)

        if self.worker_thread:
            self.worker_thread.join(timeout=timeout)
            logger.info("Celery event exporter stopped")

    def _event_consumer_loop(self) -> None:
        """Main event consumer loop running in background thread."""
        log = bind_request_context(logger, {"component": "celery-events-exporter"})
        connection = None

        try:
            connection = celery_app.connection()
            connection.connect()
            log.info("Connected to Celery broker for event stream")

            with connection.channel() as channel:
                recv = celery_app.events.Receiver(
                    connection, handlers={"*": self._handle_event}
                )
                recv.capture(limit=None, timeout=None, wakeup=True)
                log.info("Listening for Celery task events")

        except Exception as e:
            log.error("Celery event stream error", exc_info=e, extra={"error": str(e)})
        finally:
            if connection:
                connection.close()
            log.info("Event consumer loop exited")

    def _handle_event(self, event: dict) -> None:
        """Handle incoming Celery event (called by event receiver)."""
        if self.running:
            try:
                self.event_queue.put_nowait(event)
            except Exception:
                # Queue full; drop oldest and retry (simple backpressure)
                try:
                    self.event_queue.get_nowait()
                    self.event_queue.put_nowait(event)
                except Exception:
                    pass

    def _process_event(self, event: dict) -> None:
        """Process a single event and update metrics."""
        event_start = time.time()
        try:
            event_type = event.get("type", "")
            task_id = event.get("uuid", "")

            if not task_id:
                return

            # Track task lifecycle
            if event_type == "task-sent":
                self.pending_tasks[task_id]["sent_at"] = event.get("timestamp", time.time())
            elif event_type == "task-received":
                if task_id in self.pending_tasks:
                    self.pending_tasks[task_id]["received_at"] = event.get("timestamp", time.time())
            elif event_type == "task-started":
                if task_id in self.pending_tasks:
                    self.pending_tasks[task_id]["started_at"] = event.get("timestamp", time.time())
            elif event_type in ("task-succeeded", "task-failed"):
                # Task completed; record latency
                if task_id in self.pending_tasks:
                    task_data = self.pending_tasks[task_id]
                    sent_at = task_data.get("sent_at")
                    if sent_at:
                        latency = event.get("timestamp", time.time()) - sent_at
                        # Record latency with task name and result type
                        task_name = event.get("name", "unknown")
                        labels = {
                            "task_name": task_name,
                            "state": "succeeded" if event_type == "task-succeeded" else "failed",
                        }
                        task_latency_seconds.labels(**labels).observe(max(0, latency))
                    del self.pending_tasks[task_id]

            # Update queue depth metric
            task_queue_depth.set(len(self.pending_tasks))

            # Memory safety: trim old pending tasks if dict grows too large
            if len(self.pending_tasks) > self.max_pending_tasks:
                # Remove tasks older than 1 hour (shouldn't normally happen)
                cutoff_time = time.time() - 3600
                old_tasks = [
                    tid for tid, data in self.pending_tasks.items()
                    if data.get("sent_at", float("inf")) < cutoff_time
                ]
                for tid in old_tasks:
                    del self.pending_tasks[tid]

        except Exception as e:
            logger.error("Error processing event", exc_info=e, extra={"event_type": event.get("type")})
        finally:
            # Record event processing latency
            event_latency = (time.time() - event_start) * 1000  # milliseconds
            event_processing_latency_ms.observe(max(0, event_latency))
