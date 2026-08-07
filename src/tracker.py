import re
from collections.abc import Iterable

from loguru import logger

from qbittorrent import qBittorrent
from request import Request

TRACKER_URL_RE = re.compile(r"^(?:https?|udp|ws|wss)://\S+$", re.IGNORECASE)


class Tracker:
    def __init__(
        self,
        *,
        host: str,
        username: str,
        password: str,
        trackers: Iterable[str],
        trackers_url: list[str],
        proxy: str | None = None,
    ) -> None:
        self.qb = qBittorrent(host=host, username=username, password=password)
        self.req = Request(proxy=proxy)
        self.custom_trackers = set(trackers)
        self.urls = trackers_url
        self.old_trackers = set(self.qb.get_trackers())
        logger.trace(f"Trackers cache: {self.old_trackers}")

    def _get_trackers(self, url: str) -> list[str]:
        res = self.req.get(url)
        trackers = []
        for line in res.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for candidate in line.split():
                if TRACKER_URL_RE.fullmatch(candidate):
                    trackers.append(candidate)
        logger.trace(f"{url}: {trackers}")
        return trackers

    def get_trackers(self) -> list[str]:
        trackers = []
        for url in self.urls:
            trackers.extend(self._get_trackers(url))
        return trackers

    def run(self) -> None:
        trackers = set(self.get_trackers())
        trackers.update(self.custom_trackers)
        trackers.discard("")
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
