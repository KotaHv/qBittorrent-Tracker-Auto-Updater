import re
from typing import Iterable, List

from loguru import logger

from qbittorrent import qBittorrent
from request import Request

TRACKER_RE = re.compile(r"\s+")


class Tracker:
    def __init__(
        self,
        *,
        host: str,
        username: str,
        password: str,
        trackers: Iterable[str],
        trackers_url: List[str],
    ) -> None:
        self.qb = qBittorrent(host=host, username=username, password=password)
        self.req = Request()
        self.custom_trackers = set(trackers)
        self.urls = trackers_url
        self.old_trackers = set(self.qb.get_trackers())
        logger.trace(f"Trackers cache: {self.old_trackers}")

    def _get_trackers(self, url: str) -> List[str]:
        res = self.req.get(url)
        trackers = TRACKER_RE.split(res.text.strip())
        logger.trace(f"{url}: {trackers}")
        return trackers

    def get_trackers(self) -> List[str]:
        trackers = []
        for url in self.urls:
            trackers.extend(self._get_trackers(url))
        return trackers

    def run(self):
        trackers = self.custom_trackers.copy()
        trackers.update(self.get_trackers())
        if trackers == self.old_trackers:
            logger.debug("Trackers have not changed.")
            return
        rm_trackers = self.old_trackers - trackers
        if rm_trackers:
            logger.success(f"Delete trackers: {rm_trackers}")
        add_trackers = trackers - self.old_trackers
        if add_trackers:
            logger.success(f"Add trackers: {add_trackers}")
        self.qb.add_trackers_for_downloading(trackers)
        self.qb.rm_trackers_for_downloading(rm_trackers)
        self.qb.add_trackers_for_preferences(trackers)
        self.old_trackers = trackers
        logger.success("Trackers updated successfully.")
