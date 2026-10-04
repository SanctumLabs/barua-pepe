"""Publish a Celery task and verify that the exporter records its completion."""

import time

from app.exporter.celery_events_exporter import CeleryEventExporter
from app.metrics import task_latency_seconds
from app.worker.celery_app import celery_app
from app.worker.queues import BARUA_QUEUE_NAME


def main():
    exporter = CeleryEventExporter()
    exporter.start()

    try:
        if not exporter.wait_until_connected(timeout=15):
            raise RuntimeError("Exporter could not connect to the Celery broker")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if celery_app.control.ping(timeout=1):
                break
            time.sleep(1)
        else:
            raise RuntimeError("No Celery worker responded to ping")

        time.sleep(0.5)
        celery_app.send_task(
            "exporter_smoke_task",
            ignore_result=True,
            queue=BARUA_QUEUE_NAME,
        )

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            samples = (
                sample
                for family in task_latency_seconds.collect()
                for sample in family.samples
            )
            if any(
                sample.name == "barua_task_latency_seconds_count"
                and sample.labels
                == {"task_name": "exporter_smoke_task", "state": "succeeded"}
                and sample.value >= 1
                for sample in samples
            ):
                print("Exporter recorded a successful Celery task")
                return
            time.sleep(0.25)

        raise AssertionError(
            f"Exporter did not record task completion; pending={exporter.pending_tasks}"
        )
    finally:
        exporter.stop()


if __name__ == "__main__":
    main()
