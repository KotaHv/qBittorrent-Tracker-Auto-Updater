from typing import Iterable

import qbittorrentapi
from loguru import logger

from utils import retry


class qBittorrent:
    def __init__(self, *, host: str, username: str, password: str) -> None:
        self.client = qbittorrentapi.Client(
            host=host, username=username, password=password
        )
        self.login()
        logger.success("qBittorrent authentication successful.")

    @retry
    def login(self):
        self.client.auth_log_in()

    @retry
    def add_trackers_for_downloading(self, trackers: Iterable[str]):
        for torrent in self.client.torrents.info.downloading():
            logger.debug(f"{torrent.name} add trackers")
            torrent.add_trackers(urls=trackers)

    @retry
    def rm_trackers_for_downloading(self, trackers: Iterable[str]):
        for torrent in self.client.torrents.info.downloading():
            logger.debug(f"{torrent.name} remove trackers: {trackers}")
            torrent.remove_trackers(urls=trackers)

    @retry
    def add_trackers_for_preferences(self, trackers: Iterable[str]):
        self.client.app_set_preferences({"add_trackers": "\n".join(trackers)})

    @retry
    def get_trackers(self):
        preferences = self.client.app_preferences()
        trackers = preferences.add_trackers
        trackers = trackers.split("\n")
        return trackers
