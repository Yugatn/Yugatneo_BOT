import json
import pytest
from app.services.branching_dialogue import load_graph


def write_graph(tmp_path, nodes, start="start"):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps({"version": 1, "start": start, "nodes": nodes}), encoding="utf-8")
    return path


def test_builtin_graph():
    start, nodes = load_graph()
    assert start == "start"
    assert len(nodes) >= 10


def test_broken_edge_rejected(tmp_path):
    path = write_graph(tmp_path, [{"id": "start", "prompt": "Выбор?", "choices": [["Да", "missing"]]}])
    with pytest.raises(ValueError, match="Broken"):
        load_graph(path)


def test_cycle_rejected(tmp_path):
    path = write_graph(tmp_path, [{"id": "start", "prompt": "Выбор?", "choices": [["Да", "start"]]}])
    with pytest.raises(ValueError, match="cycle"):
        load_graph(path)


def test_unreachable_rejected(tmp_path):
    path = write_graph(tmp_path, [
        {"id": "start", "prompt": "Выбор?", "choices": []},
        {"id": "unused", "prompt": "Другой вопрос?", "choices": []},
    ])
    with pytest.raises(ValueError, match="Unreachable"):
        load_graph(path)


def test_duplicate_choice_rejected(tmp_path):
    path = write_graph(tmp_path, [
        {"id": "start", "prompt": "Выбор?", "choices": [["Да", "end"], ["да", "end"]]},
        {"id": "end", "prompt": "Итог?", "choices": []},
    ])
    with pytest.raises(ValueError, match="Duplicate choice"):
        load_graph(path)
