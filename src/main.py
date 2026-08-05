import sys
from time import sleep

from loguru import logger

from config import settings
from exception import RetryError
from log import setup_logger
from tracker import Tracker
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


setup_logger()
if sys.stdout.isatty():
    print(f"\033[36m{banner(APP_NAME, get_version())}\033[0m")
else:
    print(banner(APP_NAME, get_version()))
logger.info("Tracker sources:")
for url in settings.trackers_url:
    logger.info(f"  - {url}")
logger.debug(settings)


def main():
    tracker = Tracker(
        host=settings.qb_host,
        password=settings.qb_password.get_secret_value(),
        username=settings.qb_username,
        trackers=settings.trackers,
        trackers_url=settings.trackers_url,
    )
    while True:
        try:
            tracker.run()
        except RetryError:
            pass
        logger.debug(f"Wait {settings.interval} seconds.")
        sleep(settings.interval)


if __name__ == "__main__":
    main()
