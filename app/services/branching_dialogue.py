"""Validated, editable deterministic dialogue graph. No LLM required."""
import json
from dataclasses import dataclass
from pathlib import Path

GRAPH_PATH = Path(__file__).resolve().parents[2] / "data" / "dialogue_graph.ru.json"


@dataclass(frozen=True)
class BranchNode:
    prompt: str
    choices: tuple[tuple[str, str], ...]
    followup: str = ""


def load_graph(path: Path = GRAPH_PATH) -> tuple[str, dict[str, BranchNode]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        raise ValueError("Invalid dialogue graph")
    result = {}
    for raw in data["nodes"]:
        if not isinstance(raw, dict):
            raise ValueError("Invalid dialogue node")
        key, prompt, choices = raw.get("id"), raw.get("prompt"), raw.get("choices")
        if not isinstance(key, str) or not key or not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Invalid dialogue node ID or prompt")
        if key in result or not isinstance(choices, list):
            raise ValueError("Duplicate ID or invalid choices")
        parsed = []
        labels = set()
        for choice in choices:
            if (not isinstance(choice, list) or len(choice) != 2
                    or not all(isinstance(x, str) and x.strip() for x in choice)):
                raise ValueError("Invalid dialogue choice")
            label, target = choice
            if label.casefold() in labels:
                raise ValueError("Duplicate choice label")
            labels.add(label.casefold())
            parsed.append((label, target))
        result[key] = BranchNode(prompt, tuple(parsed), str(raw.get("followup", "")))
    start = data.get("start")
    if start not in result:
        raise ValueError("Missing start node")
    for node in result.values():
        for _, target in node.choices:
            if target not in result:
                raise ValueError("Broken dialogue transition")
    visited = set()
    active = set()
    def visit(node_id: str) -> None:
        if node_id in active:
            raise ValueError("Dialogue cycle detected")
        if node_id in visited:
            return
        active.add(node_id)
        for _, target in result[node_id].choices:
            visit(target)
        active.remove(node_id)
        visited.add(node_id)
    visit(start)
    if visited != set(result):
        raise ValueError("Unreachable dialogue nodes")
    return start, result


START_NODE, NODES = load_graph()


def options(node_id: str) -> tuple[str, ...]:
    return tuple(label for label, _ in NODES[node_id].choices)


def advance(node_id: str, answer: str) -> str | None:
    for label, destination in NODES[node_id].choices:
        if answer.strip().casefold() == label.casefold():
            return destination
    return None


def question_context(node_id: str) -> str:
    node = NODES[node_id]
    return ("Предложенная ветка диалога: " + node.followup + ". Вопрос: "
            + node.prompt + " Не делай диагностических выводов. "
            "Пользователь может сменить тему или отказаться от вопроса.")
