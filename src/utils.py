from collections.abc import Callable
from functools import wraps
from typing import overload

from loguru import logger

from config import settings
from exception import RetryError, StopRequested
from stop import stop_event, wait_interruptibly


@overload
def retry[**P, R](_func: Callable[P, R], *, retry_count: int = 5) -> Callable[P, R]: ...


@overload
def retry[**P, R](
    _func: None = None, *, retry_count: int = 5
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def retry[**P, R](_func: Callable[P, R] | None = None, *, retry_count: int = 5):
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        backoff_factor = 2

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            wait_time = 1
            attempts = 0
            while True:
                if stop_event.is_set():
                    raise StopRequested
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err = f"{func.__module__}:{func.__qualname__} - {e}"
                    attempts += 1
                    if attempts >= retry_count:
                        raise RetryError(err) from e
                    logger.debug(
                        f"{err} (attempt {attempts}/{retry_count}, "
                        f"retrying in {wait_time}s)"
                    )
                    wait_interruptibly(wait_time)
                    wait_time *= backoff_factor

        return wrapper

    if _func is None:
        return decorator
    return decorator(_func)


def wait_for_next_cycle() -> None:
    """Wait for the next update cycle, returning early on SIGINT/SIGTERM."""
    wait_interruptibly(settings.interval)
