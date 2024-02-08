from time import sleep

from loguru import logger

from log import setup_logger
from config import settings
from tracker import Tracker
from exception import RetryError


setup_logger()
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
