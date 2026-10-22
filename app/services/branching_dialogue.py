"""Deterministic opt-in branching dialogues; no LLM required."""
from dataclasses import dataclass

@dataclass(frozen=True)
class BranchNode:
    prompt: str
    choices: tuple[tuple[str, str], ...]
    followup: str = ""

NODES = {
    "start": BranchNode("Что сейчас хочется исследовать?", (
        ("Эмоции и состояние", "emotion"),
        ("Цель и действие", "goal"),
        ("Отношения", "relationship"),
        ("Пока не знаю", "unclear"),
    )),
    "emotion": BranchNode("Что ближе к твоему состоянию?", (
        ("Тревога", "anxiety"), ("Усталость", "fatigue"),
        ("Раздражение", "anger"), ("Другое / не уверен", "unclear"),
    )),
    "goal": BranchNode("Что сейчас мешает двигаться к цели?", (
        ("Неясно, чего хочу", "values"), ("Трудно начать", "first_step"),
        ("Не хватает ресурсов", "resources"), ("Другое", "unclear"),
    )),
    "relationship": BranchNode("Что сейчас важнее в отношениях?", (
        ("Непонимание", "communication"), ("Личные границы", "boundaries"),
        ("Конфликт", "conflict"), ("Другое", "unclear"),
    )),
    "anxiety": BranchNode("Что именно кажется неопределённым? Что известно наверняка, а что ты предполагаешь?", (), "anxiety"),
    "fatigue": BranchNode("Что сейчас больше всего истощает тебя и какой небольшой отдых доступен?", (), "stress"),
    "anger": BranchNode("Какая важная потребность или граница могла оказаться затронута?", (), "emotions"),
    "values": BranchNode("Какой результат был бы для тебя по-настоящему значимым?", (), "values"),
    "first_step": BranchNode("Какой самый маленький безопасный шаг можно сделать сегодня?", (), "goals"),
    "resources": BranchNode("Какая поддержка или ресурс уже доступны тебе?", (), "resources"),
    "communication": BranchNode("Что бы ты хотел, чтобы другой человек понял о твоём опыте?", (), "relationships"),
    "boundaries": BranchNode("Какую границу ты хотел бы обозначить спокойно и ясно?", (), "boundaries"),
    "conflict": BranchNode("Какой результат разговора был бы приемлем для обеих сторон?", (), "conflict"),
    "unclear": BranchNode("Что сейчас привлекает твоё внимание сильнее всего?", (), "situation"),
}

def options(node_id: str) -> tuple[str, ...]:
    return tuple(label for label, _ in NODES[node_id].choices)

def advance(node_id: str, answer: str) -> str | None:
    """Return the next node only for an exact explicit choice."""
    for label, destination in NODES[node_id].choices:
        if answer.strip().casefold() == label.casefold():
            return destination
    return None

def question_context(node_id: str) -> str:
    """An optional suggestion to the LLM, never an automatic diagnosis."""
    node = NODES[node_id]
    return ("Предложенная ветка диалога: " + node.followup + ". Вопрос: "
            + node.prompt + " Не делай диагностических выводов. "
            "Пользователь может сменить тему или отказаться от вопроса.")
