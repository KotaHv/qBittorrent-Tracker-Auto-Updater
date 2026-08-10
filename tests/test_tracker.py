import os
import threading
from typing import Any, cast

# Importing the tracker stack pulls in `config`, whose module-level settings
# singleton requires the qb_* credentials to be set.
os.environ.setdefault("QB_HOST", "http://localhost:8080")
os.environ.setdefault("QB_USERNAME", "admin")
os.environ.setdefault("QB_PASSWORD", "adminadmin")

import pytest

from exception import RetryError, SourceFetchError
from model import FetchSuccess
from qbittorrent import qBittorrent
from request import Request
from storage import TrackerStateStore
from tracker import Tracker


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeRequest:
    def __init__(self, sources: dict[str, str], fail: set[str] | None = None) -> None:
        self.sources = sources
        self.fail = fail or set()

    def get(self, url: str) -> FakeResponse:
        if url in self.fail:
            raise RetryError(f"failed: {url}")
        return FakeResponse(self.sources[url])


class FakeQB:
    def __init__(self, preferences: list[str] | None = None) -> None:
        self.preferences = list(preferences or [])
        self.add_calls: list[set[str]] = []
        self.rm_calls: list[set[str]] = []
        self.prefs_calls: list[list[str]] = []

    def get_trackers(self) -> list[str]:
        return list(self.preferences)

    def add_trackers_for_downloading(self, trackers) -> None:
        self.add_calls.append(set(trackers))

    def rm_trackers_for_downloading(self, trackers) -> None:
        self.rm_calls.append(set(trackers))

    def add_trackers_for_preferences(self, trackers) -> None:
        self.preferences = list(trackers)
        self.prefs_calls.append(list(trackers))


def make_tracker(
    tmp_path,
    *,
    urls: list[str],
    custom: list[str] | None = None,
    qb: Any = None,
    req: Any = None,
    store: TrackerStateStore | None = None,
) -> Tracker:
    """Build a Tracker the way main() does: create the store and load it once."""
    store_obj = store or TrackerStateStore(tmp_path / "state.json")
    store_obj.load()
    return Tracker(
        qb=cast(qBittorrent, qb if qb is not None else FakeQB()),
        req=cast(Request, req if req is not None else FakeRequest({})),
        store=store_obj,
        trackers=custom or [],
        tracker_sources=urls,
    )


def test_bootstrap_applies_diff_and_establishes_state(tmp_path):
    req = FakeRequest(
        {
            "a": "udp://t1/announce\n",
            "b": "udp://t2/announce\n",
        }
    )
    qb = FakeQB(preferences=["udp://old/announce"])
    tracker = make_tracker(tmp_path, urls=["a", "b"], qb=qb, req=req)
    tracker.bootstrap()

    # Bootstrap diffs against preferences: t1/t2 added, old removed.
    assert qb.add_calls == [{"udp://t1/announce", "udp://t2/announce"}]
    assert qb.rm_calls == [{"udp://old/announce"}]
    assert qb.preferences == ["udp://t1/announce", "udp://t2/announce"]
    state = tracker.store.state
    assert state.sources["a"] == ["udp://t1/announce"]
    assert state.sources["b"] == ["udp://t2/announce"]
    assert state.last_committed == ["udp://t1/announce", "udp://t2/announce"]

    reloaded = TrackerStateStore(tmp_path / "state.json")
    assert reloaded.load() is True
    assert reloaded.state.sources["a"] == ["udp://t1/announce"]


def test_bootstrap_without_diff_still_writes_state(tmp_path):
    req = FakeRequest({"a": "udp://t1/announce\n"})
    qb = FakeQB(preferences=["udp://t1/announce"])
    tracker = make_tracker(tmp_path, urls=["a"], qb=qb, req=req)
    tracker.bootstrap()

    assert qb.add_calls == [] and qb.rm_calls == [] and qb.prefs_calls == []
    assert TrackerStateStore(tmp_path / "state.json").load() is True


def test_candidate_keeps_custom_first_order(tmp_path):
    req = FakeRequest({"a": "udp://a/announce\n"})
    qb = FakeQB(preferences=["udp://old/announce"])
    tracker = make_tracker(
        tmp_path,
        urls=["a"],
        custom=["udp://b/announce"],
        qb=qb,
        req=req,
    )
    tracker.bootstrap()

    # Insertion order: custom trackers first, then each source in config order.
    assert qb.preferences == ["udp://b/announce", "udp://a/announce"]
    assert tracker.store.state.last_committed == [
        "udp://b/announce",
        "udp://a/announce",
    ]


def test_bootstrap_failure_raises_and_commits_nothing(tmp_path):
    req = FakeRequest({"a": "udp://t1/announce\n"}, fail={"b"})
    qb = FakeQB(preferences=["udp://old/announce"])
    tracker = make_tracker(tmp_path, urls=["a", "b"], qb=qb, req=req)

    with pytest.raises(SourceFetchError):
        tracker.bootstrap()

    assert qb.add_calls == [] and qb.rm_calls == [] and qb.prefs_calls == []
    assert TrackerStateStore(tmp_path / "state.json").load() is False


def test_t1_all_sources_succeed_diff(tmp_path):
    req = FakeRequest(
        {
            "a": "udp://t1/announce\nudp://t2/announce\n",
            "b": "udp://t2/announce\nudp://t3/announce\n",
        }
    )
    qb = FakeQB(preferences=["udp://t1/announce", "udp://old/announce"])
    tracker = make_tracker(
        tmp_path,
        urls=["a", "b"],
        custom=["udp://c1/announce"],
        qb=qb,
        req=req,
    )
    tracker.bootstrap()

    assert qb.add_calls == [
        {"udp://t2/announce", "udp://t3/announce", "udp://c1/announce"}
    ]
    assert qb.rm_calls == [{"udp://old/announce"}]
    assert qb.preferences == [
        "udp://c1/announce",
        "udp://t1/announce",
        "udp://t2/announce",
        "udp://t3/announce",
    ]

    qb.add_calls.clear()
    qb.rm_calls.clear()
    qb.prefs_calls.clear()
    tracker.run()
    assert qb.add_calls == [] and qb.rm_calls == [] and qb.prefs_calls == []

    state = tracker.store.state
    assert state.sources["a"] == ["udp://t1/announce", "udp://t2/announce"]
    assert state.sources["b"] == ["udp://t2/announce", "udp://t3/announce"]
    assert state.last_committed == [
        "udp://c1/announce",
        "udp://t1/announce",
        "udp://t2/announce",
        "udp://t3/announce",
    ]


def test_no_change_round_skips_qb(tmp_path):
    req = FakeRequest({"a": "udp://t1/announce\n"})
    qb = FakeQB(preferences=["udp://t1/announce"])
    tracker = make_tracker(tmp_path, urls=["a"], qb=qb, req=req)
    tracker.bootstrap()
    tracker.run()

    assert qb.add_calls == [] and qb.rm_calls == [] and qb.prefs_calls == []


def test_t2_source_failure_keeps_stale_trackers(tmp_path):
    req1 = FakeRequest(
        {
            "a": "udp://t1/announce\n",
            "b": "udp://t2/announce\n",
        }
    )
    qb = FakeQB(preferences=[])
    tracker = make_tracker(tmp_path, urls=["a", "b"], qb=qb, req=req1)
    tracker.bootstrap()
    tracker.run()

    req2 = FakeRequest(
        {
            "a": "udp://t1/announce\n",
            "b": "udp://t2/announce\nudp://t3/announce\n",
        },
        fail={"a"},
    )
    tracker2 = make_tracker(tmp_path, urls=["a", "b"], qb=qb, req=req2)
    tracker2.run()

    # t1 comes only from failed source a: it must survive.
    # t3 from successful source b: it must be added.
    assert qb.rm_calls == []
    assert qb.add_calls[-1] == {"udp://t3/announce"}
    assert qb.preferences == [
        "udp://t1/announce",
        "udp://t2/announce",
        "udp://t3/announce",
    ]

    state = tracker2.store.state
    assert state.sources["a"] == ["udp://t1/announce"]
    assert state.sources["b"] == ["udp://t2/announce", "udp://t3/announce"]


def test_t4_restart_uses_state_not_preferences(tmp_path):
    req = FakeRequest({"a": "udp://t1/announce\n"})
    qb = FakeQB(preferences=["udp://t1/announce"])
    tracker = make_tracker(tmp_path, urls=["a"], qb=qb, req=req)
    tracker.bootstrap()
    tracker.run()

    # A tracker manually added in qB preferences after our commit.
    qb.preferences.append("udp://manual/announce")
    qb.add_calls.clear()
    qb.rm_calls.clear()
    qb.prefs_calls.clear()

    tracker2 = make_tracker(tmp_path, urls=["a"], qb=qb, req=req)
    tracker2.run()

    # Baseline is state.last_committed, not preferences: no diff, no removal
    # of the manual tracker, no preferences overwrite.
    assert qb.add_calls == [] and qb.rm_calls == [] and qb.prefs_calls == []
    assert "udp://manual/announce" in qb.preferences


def test_t5_remove_source_cleans_its_trackers(tmp_path):
    req1 = FakeRequest(
        {
            "a": "udp://t1/announce\n",
            "b": "udp://t2/announce\n",
        }
    )
    qb = FakeQB(preferences=[])
    tracker = make_tracker(tmp_path, urls=["a", "b"], qb=qb, req=req1)
    tracker.bootstrap()
    tracker.run()

    tracker2 = make_tracker(tmp_path, urls=["a"], qb=qb, req=req1)
    tracker2.run()

    assert qb.rm_calls[-1] == {"udp://t2/announce"}
    assert "b" not in tracker2.store.state.sources


def test_t5b_new_source_fails_first_fetch(tmp_path):
    req1 = FakeRequest({"a": "udp://t1/announce\n"})
    qb = FakeQB(preferences=[])
    tracker = make_tracker(tmp_path, urls=["a"], qb=qb, req=req1)
    tracker.bootstrap()
    tracker.run()
    qb.add_calls.clear()
    qb.rm_calls.clear()
    qb.prefs_calls.clear()

    req2 = FakeRequest({"a": "udp://t1/announce\n"}, fail={"c"})
    tracker2 = make_tracker(tmp_path, urls=["a", "c"], qb=qb, req=req2)
    tracker2.run()

    # Failed new source has no history: it contributes nothing and deletes nothing.
    assert qb.add_calls == [] and qb.rm_calls == []
    assert "c" not in tracker2.store.state.sources


def test_t8_fetch_all_is_concurrent(tmp_path):
    urls = ["u0", "u1", "u2"]
    n = len(urls)
    barrier = threading.Barrier(n, timeout=5)

    class ConcurrentRequest:
        def get(self, url: str) -> FakeResponse:
            barrier.wait()
            return FakeResponse(f"udp://{url}/announce\n")

    tracker = make_tracker(tmp_path, urls=urls, req=ConcurrentRequest())
    results = tracker.fetch_all()

    assert all(isinstance(result, FetchSuccess) for result in results.values())
    all_trackers = {
        t
        for result in results.values()
        if isinstance(result, FetchSuccess)
        for t in result.trackers
    }
    assert all_trackers == {f"udp://{url}/announce" for url in urls}
