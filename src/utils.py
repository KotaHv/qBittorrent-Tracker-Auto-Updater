from collections.abc import Callable
from functools import wraps
from typing import overload

from loguru import logger
from qbittorrentapi.exceptions import HTTP403Error, LoginFailed

from config import settings
from exception import QBLoginFailedError, RetryError, StopRequested
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
                except LoginFailed as e:
                    # Re-authentication was rejected (e.g. the password changed
                    # on qBittorrent): retrying only adds failed-login attempts
                    # until qBittorrent temporarily bans this IP.
                    raise QBLoginFailedError(
                        "qBittorrent login failed: QB_USERNAME / QB_PASSWORD "
                        "were rejected during re-authentication, or this IP "
                        "was temporarily banned after too many failed attempts."
                    ) from e
                except HTTP403Error as e:
                    # A forbidden request means the API key/credentials are no
                    # longer accepted (or the IP is banned); retrying cannot
                    # fix it and would only make the ban worse.
                    reason = str(e).strip() or (
                        "the API key or credentials may have changed on "
                        "qBittorrent, or this IP was temporarily banned"
                    )
                    raise QBLoginFailedError(
                        f"qBittorrent request forbidden (HTTP 403): {reason}"
                    ) from e
                except Exception as e:
                    err = f"{func.__module__}:{func.__qualname__} - {e}"
                    attempts += 1
                    if attempts >= retry_count:
                        raise RetryError(err) from e
                    logger.debug(
                        "{} (attempt {}/{}, retrying in {}s)",
                        err,
                        attempts,
                        retry_count,
                        wait_time,
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


def log_fatal_qb_error(exc: Exception) -> None:
    """Explain a fatal qBittorrent error and why the app will not exit.

    Exiting on a qBittorrent error is dangerous under Docker
    ``restart: always``: the container restarts immediately and retries; for
    rejected logins every restart is another failed attempt, and qBittorrent
    eventually bans the IP. So instead of exiting we log the problem once and
    wait for manual intervention.
    """
    logger.error(str(exc))
    logger.error(
        "The app will not retry or exit (a Docker restart loop would burn "
        "through failed-login attempts until qBittorrent temporarily bans "
        "this IP). Fix the qBittorrent connection or credentials, then "
        "restart the container, e.g. `docker compose restart`."
    )


def handle_fatal_qb_error(exc: Exception) -> None:
    """Log a fatal qBittorrent error, then wait for manual intervention.

    Staying alive instead of exiting keeps Docker's restart policy from
    restart-looping and burning through failed-login attempts until
    qBittorrent temporarily bans this IP.
    """
    log_fatal_qb_error(exc)
    stop_event.wait()
    logger.info("Received interrupt, shutting down gracefully.")
