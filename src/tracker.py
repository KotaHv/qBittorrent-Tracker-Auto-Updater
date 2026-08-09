import os
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal, overload

from loguru import logger

from exception import RetryError, SourceFetchError
from model import (
    FetchFailure,
    FetchResult,
    FetchResults,
    FetchSuccess,
    Sources,
    StrictFetchResults,
    Trackers,
)
from qbittorrent import qBittorrent
from request import Request
from storage import TrackerStateStore

TRACKER_URL_RE = re.compile(r"^(?:https?|udp|ws|wss)://\S+$", re.IGNORECASE)


class Tracker:
    def __init__(
        self,
        *,
        qb: qBittorrent,
        req: Request,
        store: TrackerStateStore,
        trackers: Iterable[str],
        trackers_url: list[str],
    ) -> None:
        self.qb = qb
        self.req = req
        self.store = store
        self.custom_trackers = trackers
        self.trackers_url = list(trackers_url)
        logger.debug(
            f"Tracker state: sources={self.store.state.sources}, "
            f"last_committed={self.store.state.last_committed}"
        )

    def _get_trackers(self, url: str) -> Trackers:
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

    def _fetch_one(self, url: str) -> FetchResult:
        try:
            trackers = self._get_trackers(url)
        except RetryError as e:
            logger.warning(f"Failed to fetch tracker source {url}: {e}")
            return FetchFailure(url=url)
        return FetchSuccess(url=url, trackers=trackers)

    @overload
    def fetch_all(self, *, strict: Literal[True]) -> StrictFetchResults: ...

    @overload
    def fetch_all(self, *, strict: Literal[False] = False) -> FetchResults: ...

    def fetch_all(self, *, strict: bool = False) -> FetchResults | StrictFetchResults:
        """Fetch every source concurrently; a failed source does not block others.

        With ``strict=True`` a failed source raises :class:`SourceFetchError`
        instead of being collected as a failure.
        """
        results = {}
        if not self.trackers_url:
            return results
        max_workers = min(len(self.trackers_url), os.process_cpu_count() or 4)
        pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="tracker-fetch"
        )
        futures = {pool.submit(self._fetch_one, url): url for url in self.trackers_url}
        try:
            for future in as_completed(futures):
                result = future.result()
                if strict and isinstance(result, FetchFailure):
                    raise SourceFetchError(f"Failed to fetch all sources: {result.url}")
                results[result.url] = result
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        return results

    def _diff(
        self, candidate: list[str], baseline: set[str]
    ) -> tuple[set[str], set[str]]:
        """Compute trackers to add and to remove."""
        candidate_set = set(candidate)
        return candidate_set - baseline, baseline - candidate_set

    def _apply(
        self, add_trackers: set[str], rm_trackers: set[str], candidate: list[str]
    ) -> None:
        """Apply the diff to qBittorrent: add, remove, then update preferences."""
        if add_trackers:
            logger.success(f"Add trackers: {add_trackers}")
            self.qb.add_trackers_for_downloading(add_trackers)
        if rm_trackers:
            logger.success(f"Delete trackers: {rm_trackers}")
            self.qb.rm_trackers_for_downloading(rm_trackers)

        self.qb.add_trackers_for_preferences(candidate)

    def bootstrap(self) -> None:
        """First sync before any valid state exists: all sources must succeed,
        qB preferences are the baseline, and the initial history is persisted."""
        results = self.fetch_all(strict=True)
        candidate: list[str] = []
        for t in self.custom_trackers:
            if t not in candidate:
                candidate.append(t)
        new_sources: Sources = {}
        for url in self.trackers_url:
            result = results[url]
            trackers = result.trackers
            new_sources[url] = trackers
            for t in trackers:
                if t not in candidate:
                    candidate.append(t)

        baseline = set(self.qb.get_trackers())
        add_trackers, rm_trackers = self._diff(candidate, baseline)
        if add_trackers or rm_trackers:
            self._apply(add_trackers, rm_trackers, candidate)
        # Always persist the initial history so later cycles use run().
        self.store.commit(new_sources, candidate)
        logger.success("Initial tracker state established.")

    def run(self) -> None:
        results = self.fetch_all()
        prev_sources = self.store.state.sources

        candidate: list[str] = []
        for t in self.custom_trackers:
            if t not in candidate:
                candidate.append(t)
        new_sources: Sources = {}
        for url in self.trackers_url:
            result = results[url]
            if isinstance(result, FetchSuccess):
                trackers = result.trackers
            else:
                trackers = prev_sources.get(url, [])
            new_sources[url] = trackers
            for t in trackers:
                if t not in candidate:
                    candidate.append(t)

        add_trackers, rm_trackers = self._diff(
            candidate, set(self.store.state.last_committed)
        )
        if not add_trackers and not rm_trackers:
            logger.debug("Trackers have not changed.")
            return
        self._apply(add_trackers, rm_trackers, candidate)
        self.store.commit(new_sources, candidate)
        logger.success("Trackers updated successfully.")
