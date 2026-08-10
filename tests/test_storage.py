import json

import pytest

from exception import StateSaveError
from storage import TrackerStateStore


def test_load_missing_file_returns_false(tmp_path):
    store = TrackerStateStore(tmp_path / "state.json")
    assert store.load() is False
    assert store.state.sources == {}


def test_atomic_write_keeps_old_file_on_failure(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    store = TrackerStateStore(path)
    store.state.sources = {"u1": ["t1"]}
    store.state.last_committed = ["t1"]
    store.save()
    old = path.read_text(encoding="utf-8")

    def boom(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr("os.replace", boom)
    store.state.sources = {"u1": ["t2"]}
    with pytest.raises(StateSaveError):
        store.save()

    assert path.read_text(encoding="utf-8") == old
    assert {p.name for p in tmp_path.iterdir()} == {"state.json"}


def test_temp_file_creation_permission_error_is_wrapped(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    store = TrackerStateStore(path)
    store.state.sources = {"u1": ["t1"]}
    store.state.last_committed = ["t1"]

    def deny(**_kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("tempfile.NamedTemporaryFile", deny)
    with pytest.raises(StateSaveError) as exc_info:
        store.save()

    assert isinstance(exc_info.value.__cause__, PermissionError)
    assert {p.name for p in tmp_path.iterdir()} == set()


def test_commit_updates_and_persists_state(tmp_path):
    path = tmp_path / "state.json"
    store = TrackerStateStore(path)
    store.commit(
        {"a": ["t1"]},
        ["t1", "t2"],
    )

    assert store.state.sources == {"a": ["t1"]}
    assert store.state.last_committed == ["t1", "t2"]
    assert store.state.updated_at

    loaded = TrackerStateStore(path)
    assert loaded.load() is True
    assert loaded.state.last_committed == ["t1", "t2"]


def test_schema_mismatch_backs_up_and_returns_false(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"schema_version": 2, "sources": {}}))
    store = TrackerStateStore(path)
    assert store.load() is False
    assert store.state.sources == {}
    backups = list(tmp_path.glob("state.json.bak-*"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8"))["schema_version"] == 2


def test_corrupt_json_backs_up_and_returns_false(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not json")
    store = TrackerStateStore(path)
    assert store.load() is False
    assert store.state.sources == {}
    assert list(tmp_path.glob("state.json.bak-*"))
