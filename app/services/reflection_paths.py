"""Voluntary, non-clinical reflection exercises used by Telegram polling MVP.

These prompts do not deliver psychotherapy, diagnosis or guaranteed outcomes.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ReflectionPath:
    key: str
    title: str
    description: str
    questions: tuple[str, ...]

PATHS = {
    "cbt": ReflectionPath(
        "cbt", "Мысли и реакции (по мотивам КПТ)",
        "Наблюдение за ситуацией, мыслями и альтернативными объяснениями.",
        (
            "Опиши конкретную ситуацию без оценок. Что произошло?",
            "Какая мысль появилась первой? Какие чувства ты заметил?",
            "Какие факты поддерживают эту мысль, а какие ей противоречат?",
            "Какое другое объяснение возможно, и какой небольшой шаг ты выберешь?",
        ),
    ),
    "gestalt": ReflectionPath(
        "gestalt", "Осознавание настоящего (гештальт-подход)",
        "Мягкое наблюдение за текущими ощущениями и потребностями.",
        (
            "Что ты замечаешь вокруг себя прямо сейчас?",
            "Если комфортно, что замечаешь в теле? Можно пропустить.",
            "Какую потребность ты сейчас осознаёшь?",
            "Что могло бы поддержать тебя сегодня, без давления на себя?",
        ),
    ),
    "coaching": ReflectionPath(
        "coaching", "Цели и действия (коучинг)",
        "Уточнение выбранной цели и первого осуществимого шага.",
        (
            "Что ты хочешь изменить, своими словами?",
            "Почему именно эта цель для тебя важна?",
            "Какие ресурсы и препятствия ты замечаешь?",
            "Какой небольшой шаг сделаешь и когда проверишь результат?",
        ),
    ),
}

def render_step(path: ReflectionPath, index: int) -> str:
    return (f"{path.title}: вопрос {index + 1}/{len(path.questions)}\n\n"
            f"{path.questions[index]}\n\n"
            "Ответ можно пропустить командой /skip. Выход: /cancel.")
