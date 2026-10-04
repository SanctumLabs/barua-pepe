"""Celery event stream consumer and Prometheus exporter."""

import logging
import socket
import threading
import time
from typing import Dict, Optional

from kombu.exceptions import ChannelError, OperationalError

from app.metrics import (
    task_latency_seconds,
    task_pending_count,
    task_queue_depth,
    event_processing_latency_ms,
)
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class CeleryEventExporter:
    """
    Consumes Celery task events via the event stream and updates Prometheus metrics.

    Tracks:
    - Task execution latency (started → succeeded/failed)
    - Tracked tasks observed from sent/started through completion
    - Ready messages in configured broker queues
    - Event processing latency

    Runs in a background thread to avoid blocking the main app.
    """

    def __init__(
        self,
        max_pending_tasks: int = 100000,
        pending_task_ttl: float = 3600,
        queue_depth_poll_interval: float = 10,
    ):
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self._receiver = None
        self._connection = None
        self._connected = threading.Event()
        self._stop_event = threading.Event()

        self.pending_tasks: Dict[str, dict] = {}
        self.max_pending_tasks = max_pending_tasks
        self.pending_task_ttl = pending_task_ttl
        self.queue_depth_poll_interval = queue_depth_poll_interval
        self._last_queue_depth_poll = 0.0

    def wait_until_connected(self, timeout: float) -> bool:
        """Wait for the event stream connection to become ready."""
        return self._connected.wait(timeout)

    def start(self) -> None:
        """Start the event consumer thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Event exporter already running")
            return

        self.running = True
        self._stop_event.clear()
        self._connected.clear()
        self.worker_thread = threading.Thread(
            target=self._event_consumer_loop, daemon=True, name="celery-events-exporter"
        )
        self.worker_thread.start()
        logger.info("Celery event exporter started")

    def stop(self, timeout: int = 5) -> None:
        """Stop the event consumer thread."""
        if not self.running:
            return

        self.running = False
        self._stop_event.set()
        if self._receiver:
            self._receiver.should_stop = True

        if self.worker_thread:
            self.worker_thread.join(timeout=timeout)
            if self.worker_thread.is_alive():
                logger.error(
                    "Celery event exporter did not stop within %s seconds", timeout
                )
                return
            logger.info("Celery event exporter stopped")

    def _event_consumer_loop(self) -> None:
        """Main event consumer loop running in background thread."""
        retry_delay = 1.0

        try:
            while self.running:
                connection = None
                try:
                    connection = celery_app.connection()
                    self._connection = connection
                    connection.connect()
                    logger.info("Connected to Celery broker for event stream")
                    self._update_queue_depth(connection)
                    logger.info("Listening for Celery task events")

                    self._receiver = celery_app.events.Receiver(
                        connection, handlers={"*": self._handle_event}
                    )
                    self._connected.set()
                    retry_delay = 1.0
                    if not self.running:
                        self._receiver.should_stop = True
                    self._receiver.capture(
                        limit=None, timeout=self.queue_depth_poll_interval, wakeup=True
                    )
                except socket.timeout:
                    pass
                except (OperationalError, OSError, ChannelError) as error:
                    if self.running:
                        logger.error(
                            "Celery event stream error; retrying in %.1f seconds: %s",
                            retry_delay,
                            error,
                            exc_info=True,
                        )
                finally:
                    self._receiver = None
                    self._connected.clear()
                    self._connection = None
                    if connection and connection.connected:
                        try:
                            connection.close()
                        except (OperationalError, OSError) as error:
                            logger.warning(
                                "Error closing Celery broker connection: %s", error
                            )

                if self.running and self._stop_event.wait(retry_delay):
                    break
                retry_delay = min(retry_delay * 2, 30.0)
        finally:
            self.running = False
            self._receiver = None
            self._connection = None
            self._connected.clear()
            logger.info("Celery event consumer loop exited")

    def _handle_event(self, event: dict) -> None:
        """Handle incoming Celery event (called by event receiver)."""
        if self.running:
            self._process_event(event)

    def _process_event(self, event: dict) -> None:
        """Process a single event and update metrics."""
        event_start = time.perf_counter()
        try:
            task_id = event.get("uuid", "")
            if task_id:
                self._update_task_state(event, task_id)
                self._trim_pending_tasks()
            self._maybe_update_queue_depth()
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error processing Celery event: %s", e, exc_info=True)
        finally:
            task_pending_count.set(len(self.pending_tasks))
            event_latency = (time.perf_counter() - event_start) * 1000
            event_processing_latency_ms.observe(max(0, event_latency))

    def _update_task_state(self, event: dict, task_id: str) -> None:
        """Update tracked state from one task lifecycle event."""
        event_type = event.get("type", "")
        if event_type in ("task-sent", "task-received"):
            task_data = self.pending_tasks.setdefault(task_id, {})
            timestamp_key = "sent_at" if event_type == "task-sent" else "received_at"
            task_data[timestamp_key] = event.get("timestamp", time.time())
            task_data["name"] = event.get("name", task_data.get("name", "unknown"))
        elif event_type == "task-started":
            self.pending_tasks.setdefault(task_id, {})["started_at"] = event.get(
                "timestamp", time.time()
            )
        elif event_type in ("task-succeeded", "task-failed"):
            self._record_task_completion(event, task_id, event_type)

    def _record_task_completion(
        self, event: dict, task_id: str, event_type: str
    ) -> None:
        """Observe execution time and forget the completed task."""
        task_data = self.pending_tasks.pop(task_id, {})
        started_at = task_data.get("started_at")
        if started_at is None:
            return

        elapsed = event.get("runtime")
        if elapsed is None:
            elapsed = event.get("timestamp", time.time()) - started_at
        task_latency_seconds.labels(
            task_name=event.get("name", task_data.get("name", "unknown")),
            state="succeeded" if event_type == "task-succeeded" else "failed",
        ).observe(max(0, elapsed))

    def _trim_pending_tasks(self) -> None:
        """Drop expired entries and then enforce the pending-task bound."""
        cutoff_time = time.time() - self.pending_task_ttl
        expired = [
            task_id
            for task_id, data in self.pending_tasks.items()
            if min(
                (
                    data[key]
                    for key in ("sent_at", "received_at", "started_at")
                    if key in data
                ),
                default=float("inf"),
            )
            < cutoff_time
        ]
        for task_id in expired:
            del self.pending_tasks[task_id]

        excess_count = len(self.pending_tasks) - self.max_pending_tasks
        for task_id in list(self.pending_tasks)[:excess_count]:
            del self.pending_tasks[task_id]

    def _maybe_update_queue_depth(self) -> None:
        """Poll actual broker queue depth at a bounded interval."""
        if not self._connection:
            return

        now = time.monotonic()
        if now - self._last_queue_depth_poll < self.queue_depth_poll_interval:
            return

        self._update_queue_depth(self._connection)

    def _update_queue_depth(self, connection) -> None:
        """Update ready-message counts for configured Celery queues."""
        for queue in celery_app.conf.task_queues:
            channel = connection.channel()
            try:
                declaration = channel.queue_declare(queue=queue.name, passive=True)
            except ChannelError as error:
                logger.warning(
                    "Could not read depth for Celery queue %s: %s",
                    queue.name,
                    error,
                )
            else:
                task_queue_depth.labels(queue_name=queue.name).set(
                    declaration.message_count
                )
            finally:
                channel.close()

        self._last_queue_depth_poll = time.monotonic()
