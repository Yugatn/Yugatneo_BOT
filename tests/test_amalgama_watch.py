import json
from amalgama.cli import main as baseline_main
from amalgama.watch import compare, watch


def test_compare():
    assert compare({"a": {"sha256": "1"}, "b": {"sha256": "1"}},
                   {"a": {"sha256": "2"}, "c": {"sha256": "3"}}) == {
        "added": ["c"], "removed": ["b"], "changed": ["a"]}


def test_watch_detects_changes(tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    target = root / "sample.txt"
    target.write_text("first")
    state = tmp_path / "state.json"
    assert baseline_main(["init", "--root", str(root), "--state", str(state)]) == 0
    events = []
    def fake_sleep(_):
        target.write_text("second")
    watch(root, state, interval=1, iterations=2, sleep=fake_sleep, emit=events.append)
    assert len(events) == 1
    assert json.loads(events[0])["changed"] == ["sample.txt"]


def test_watch_rejects_other_directory(tmp_path):
    import pytest
    root = tmp_path / "one"
    root.mkdir()
    other = tmp_path / "two"
    other.mkdir()
    state = tmp_path / "state.json"
    assert baseline_main(["init", "--root", str(root), "--state", str(state)]) == 0
    with pytest.raises(ValueError):
        watch(other, state, iterations=1, sleep=lambda _: None)
