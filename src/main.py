import sys
from time import sleep

from loguru import logger

from exception import (
    InvalidSettingsError,
    QBitTorrentError,
    RetryError,
    SourceFetchError,
    StateSaveError,
    StopRequested,
)

try:
    from config import settings
except InvalidSettingsError as exc:
    print(f"Configuration error:\n{exc}", file=sys.stderr)
    sys.exit(1)

from log import setup_logger
from qbittorrent import qBittorrent
from request import Request
from stop import register_signal_handlers, stop_event
from storage import TrackerStateStore
from tracker import Tracker
from utils import wait_for_next_cycle
from version import get_version

APP_NAME = "qBittorrent Tracker Auto Updater"


def banner(title: str, version: str) -> str:
    text = f"Starting {title} v{version}"
    width = len(text) + 8
    border = "═" * width
    blank = " " * width
    padding = " " * 4
    return "\n".join(
        (
            f"╔{border}╗",
            f"║{blank}║",
            f"║{padding}{text}{padding}║",
            f"║{blank}║",
            f"╚{border}╝",
        )
    )


def show_startup_info() -> None:
    """Print the startup banner and log the configured tracker sources."""
    banner_text = banner(APP_NAME, get_version())
    if sys.stderr.isatty():
        banner_text = f"\033[36m{banner_text}\033[0m"
    print(banner_text, file=sys.stderr)
    logger.info("Tracker sources:")
    if settings.tracker_sources:
        for url in settings.tracker_sources:
            logger.info(f"  - {url}")
    else:
        logger.info("  (none)")
    if settings.trackers:
        logger.info("Custom trackers:")
        for tracker in settings.trackers:
            logger.info(f"  - {tracker}")
    else:
        logger.info("No custom trackers configured.")
    logger.debug(settings)


def log_fatal_qb_error(exc: Exception) -> None:
    """Explain a fatal qBittorrent startup error and why the app will not exit.

    Exiting on a qBittorrent error is dangerous under Docker
    ``restart: always``: the container restarts immediately and retries; for
    rejected logins every restart is another failed attempt, and qBittorrent
    eventually bans the IP. So instead of exiting we log the problem once and
    wait for manual intervention.
    """
    logger.error(f"qBittorrent error: {exc}")
    logger.error(
        "The app will not retry or exit (a Docker restart loop would burn "
        "through failed-login attempts until qBittorrent temporarily bans "
        "this IP). Fix the qBittorrent connection or credentials, then "
        "restart the container, e.g. `docker compose restart`."
    )


def main():
    setup_logger()
    show_startup_info()

    if settings.uses_deprecated_trackers_url:
        logger.warning(
            "The `trackers_url` setting is deprecated; use `tracker_sources` instead."
        )

    # Install the handler before connecting so a stop during startup (login
    # retries) is graceful too, instead of leaving Docker to SIGKILL the
    # container after its stop grace period.
    register_signal_handlers()

    try:
        qb = qBittorrent(
            host=settings.qb_host.unicode_string(),
            username=settings.qb_username,
            password=settings.qb_password.get_secret_value(),
        )
    except StopRequested:
        logger.info("Received interrupt, shutting down gracefully.")
        return
    except QBitTorrentError as exc:
        log_fatal_qb_error(exc)
        # Stay alive so Docker's restart policy cannot restart-loop us; the
        # process only exits on SIGINT/SIGTERM, i.e. a deliberate restart.
        while not stop_event.is_set():
            sleep(0.5)
        logger.info("Received interrupt, shutting down gracefully.")
        return

    req = Request(proxy=settings.proxy.unicode_string() if settings.proxy else None)
    store = TrackerStateStore(settings.state_file)
    tracker = Tracker(
        qb=qb,
        req=req,
        store=store,
        trackers=settings.trackers,
        tracker_sources=settings.tracker_sources,
    )

    try:
        if not store.load():
            while not stop_event.is_set():
                try:
                    tracker.bootstrap()
                    break
                except (RetryError, SourceFetchError, StateSaveError) as e:
                    logger.warning(f"Bootstrap failed: {e}; will retry next cycle.")
                    store.load()
                finally:
                    wait_for_next_cycle()

        while not stop_event.is_set():
            try:
                tracker.run()
            except (RetryError, StateSaveError) as e:
                logger.warning(f"Tracker update failed: {e}, will retry next cycle.")
                store.load()
            if not stop_event.is_set():
                logger.debug(f"Wait {settings.interval} seconds.")
                wait_for_next_cycle()
    except StopRequested:
        logger.info("Received interrupt, shutting down gracefully.")
        return

    logger.info("Received interrupt, shutting down gracefully.")


if __name__ == "__main__":
    try:
        main()
    except StopRequested:
        logger.info("Forced exit.")
