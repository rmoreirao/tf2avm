from __future__ import annotations

import time
import functools
import structlog
from typing import Any, Callable

logger = structlog.get_logger()


def agent_step(name: str):
    """Decorator to wrap agent step execution with timing & error logging."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            logger.info("agent.start", step=name)
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start) * 1000)
                logger.info(
                    "agent.success", step=name, duration_ms=duration_ms, summary=_summarize(result)
                )
                return result
            except Exception as e:  # noqa
                duration_ms = int((time.time() - start) * 1000)
                logger.error(
                    "agent.error", step=name, duration_ms=duration_ms, error=str(e)
                )
                raise

        return wrapper

    return decorator


def _summarize(result: Any) -> dict:
    try:
        if hasattr(result, "model_dump"):
            data = result.model_dump()
            # Light summary only
            return {k: v for k, v in data.items() if k in {"status", "converted_repo_path"}}
        return {"type": type(result).__name__}
    except Exception:  # pragma: no cover
        return {"summary": "n/a"}
