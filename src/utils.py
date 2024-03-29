import time
from functools import wraps

from loguru import logger

from exception import RetryError
from config import settings


def retry(_func=None, *, retry_count: int = 5):
    def decorator(func):
        backoff_factor = 2

        @wraps(func)
        def wrapper(*args, **kwargs):
            wait_time = 1
            attempts = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    e = f"{func.__module__}:{func.__qualname__} - {e}"
                    attempts += 1
                    if attempts >= retry_count:
                        if settings.debug:
                            logger.exception(e)
                        else:
                            logger.error(e)
                        raise RetryError(e)
                    logger.debug(e)
                    time.sleep(wait_time)
                    wait_time *= backoff_factor

        return wrapper

    if _func is None:
        return decorator
    else:
        return decorator(_func)
