"""Immediate, bounded retries of an already authorized, idempotent storage step."""
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps

from .control_plane import ControlPlaneError


@dataclass
class SaveRetryBudget:
    remaining: int = 2


_budget: ContextVar[SaveRetryBudget | None] = ContextVar('save_retry_budget', default=None)


def with_save_retries(function):
    """Nested preview/project/view saves share two retries, not two per layer."""
    @wraps(function)
    async def wrapped(*args, **kwargs):
        if _budget.get() is not None:
            return await function(*args, **kwargs)
        token = _budget.set(SaveRetryBudget())
        try:
            return await function(*args, **kwargs)
        finally:
            _budget.reset(token)
    return wrapped


def transient_storage_error(error):
    # Do not retry authentication, validation, expiry, revision conflicts or
    # rate limits (which may require a Retry-After delay). No background tasks.
    return isinstance(error, ControlPlaneError) and error.status_code in (408, 500, 502, 503, 504)


async def retry_storage(operation):
    """Retry only the failed step; a failed verification never repeats its write."""
    while True:
        try:
            return await operation()
        except ControlPlaneError as error:
            budget = _budget.get()
            if budget is None or budget.remaining == 0 or not transient_storage_error(error):
                raise
            budget.remaining -= 1
