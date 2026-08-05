import time
from collections.abc import Callable
from functools import wraps
from typing import overload

from loguru import logger

from config import settings
from exception import RetryError


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
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 - retries must handle errors from arbitrary wrapped code
                    err = f"{func.__module__}:{func.__qualname__} - {e}"
                    attempts += 1
                    if attempts >= retry_count:
                        if settings.debug:
                            logger.exception(f"{err} (after {attempts} attempts)")
                        else:
                            logger.error(f"{err} (after {attempts} attempts)")
                        raise RetryError(err) from e
                    logger.debug(
                        f"{err} (attempt {attempts}/{retry_count}, "
                        f"retrying in {wait_time}s)"
                    )
                    time.sleep(wait_time)
                    wait_time *= backoff_factor

        return wrapper

    if _func is None:
        return decorator
    return decorator(_func)
