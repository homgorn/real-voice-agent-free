from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from voiceagent_api.config import settings
from voiceagent_api.schemas import utc_now
from voiceagent_api.store import AgentStore, store

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkerCycleResult:
    processed: int
    delivered: int
    retry_scheduled: int
    failed: int


class WebhookDeliveryWorker:
    def __init__(
        self,
        *,
        store_instance: AgentStore,
        organization_id: str,
        poll_interval_seconds: float,
        batch_size: int,
        sleep_fn: Callable[[float], None] | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store_instance
        self.organization_id = organization_id
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self.sleep_fn = sleep_fn or time.sleep
        self.now_fn = now_fn or utc_now

    def run_once(self) -> WorkerCycleResult:
        record = self.store.process_webhook_deliveries(
            organization_id=self.organization_id,
            now=self.now_fn(),
            limit=self.batch_size,
        )
        result = WorkerCycleResult(
            processed=record["processed"],
            delivered=record["delivered"],
            retry_scheduled=record["retry_scheduled"],
            failed=record["failed"],
        )
        logger.info(
            "webhook worker cycle processed=%s delivered=%s retry_scheduled=%s failed=%s",
            result.processed,
            result.delivered,
            result.retry_scheduled,
            result.failed,
        )
        return result

    def run_forever(self, *, max_cycles: int | None = None) -> None:
        cycle_count = 0
        while True:
            self.run_once()
            cycle_count += 1
            if max_cycles is not None and cycle_count >= max_cycles:
                return
            self.sleep_fn(self.poll_interval_seconds)


def build_worker() -> WebhookDeliveryWorker:
    return WebhookDeliveryWorker(
        store_instance=store,
        organization_id=settings.default_organization_id,
        poll_interval_seconds=settings.webhook_worker_poll_interval_seconds,
        batch_size=settings.webhook_delivery_batch_size,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceAgent webhook delivery worker")
    parser.add_argument("--once", action="store_true", help="Process one polling cycle and exit")
    parser.add_argument("--max-cycles", type=int, default=None, help="Run a fixed number of cycles and exit")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    worker = build_worker()
    if args.once:
        worker.run_once()
        return
    worker.run_forever(max_cycles=args.max_cycles)


if __name__ == "__main__":
    main()
