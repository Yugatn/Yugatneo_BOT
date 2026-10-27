import json
from pathlib import Path
from amalgama.cli import main


def test_baseline_and_detection(tmp_path, capsys):
    root = tmp_path / "watched"
    root.mkdir()
    state = tmp_path / "private" / "baseline.json"
    (root / "example.txt").write_text("first", encoding="utf-8")
    args = ["--root", str(root), "--state", str(state)]
    assert main(["init", *args]) == 0
    assert main(["scan", *args]) == 0
    (root / "example.txt").write_text("second", encoding="utf-8")
    assert main(["scan", *args]) == 1
    assert "example.txt" in capsys.readouterr().out


def test_baseline_not_overwritten(tmp_path):
    root = tmp_path / "watched"
    root.mkdir()
    state = tmp_path / "baseline.json"
    args = ["--root", str(root), "--state", str(state)]
    assert main(["init", *args]) == 0
    assert main(["init", *args]) == 2


def test_reject_state_inside_root(tmp_path):
    root = tmp_path / "watched"
    root.mkdir()
    assert main(["init", "--root", str(root), "--state", str(root / "baseline.json")]) == 2
