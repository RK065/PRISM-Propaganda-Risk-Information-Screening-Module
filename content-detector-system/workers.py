"""
Background worker queue using asyncio.Queue.
No Celery or external broker required.

Usage:
    await enqueue("fact_check", {"text": "...", "analysis_id": 1})
    # Worker runs in background and calls registered handlers.
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("workers")

_queue: asyncio.Queue = asyncio.Queue()
_handlers: dict[str, Callable[..., Coroutine]] = {}
_worker_task: asyncio.Task | None = None


def register(task_type: str):
    """Decorator to register an async handler for a task type."""
    def decorator(fn: Callable[..., Coroutine]):
        _handlers[task_type] = fn
        return fn
    return decorator


async def enqueue(task_type: str, payload: dict[str, Any]) -> None:
    await _queue.put({"type": task_type, "payload": payload})
    logger.debug("Enqueued task type=%s", task_type)


async def _run_worker() -> None:
    logger.info("Background worker started")
    while True:
        task = await _queue.get()
        task_type = task["type"]
        handler = _handlers.get(task_type)
        if handler is None:
            logger.warning("No handler registered for task type: %s", task_type)
        else:
            try:
                await handler(**task["payload"])
            except Exception:
                logger.exception("Worker error processing task type=%s", task_type)
        _queue.task_done()


def start_worker() -> None:
    """Start the background worker. Call once at app startup."""
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.ensure_future(_run_worker())
        logger.info("Worker task scheduled")


def stop_worker() -> None:
    """Cancel the background worker. Call at app shutdown."""
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        logger.info("Worker task cancelled")


def queue_size() -> int:
    return _queue.qsize()


# ---- built-in task handlers ----

@register("fact_check_async")
async def _handle_fact_check(text: str, analysis_id: int) -> None:
    """
    Run full multi-source fact-check in background and log results.
    Results could be persisted to DB here — extend as needed.
    """
    from advanced_fact_checking import MultiSourceFactChecker
    checker = MultiSourceFactChecker()
    results = checker.check_all_sources(text)
    logger.info(
        "Async fact-check complete analysis_id=%d results=%d",
        analysis_id, len(results),
    )
    # TODO: persist results to a fact_check_results table


@register("high_risk_alert")
async def _handle_high_risk_alert(analysis_id: int, risk_score: float, classification: str) -> None:
    """Placeholder: send alert (email/webhook) for high-risk content."""
    logger.warning(
        "HIGH RISK ALERT analysis_id=%d risk=%.1f classification=%s",
        analysis_id, risk_score, classification,
    )
    # TODO: integrate with email/Slack/webhook
