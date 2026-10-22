"""Небольшой каталог добровольных практик для первого Telegram MVP.

Длительность — ориентир, переход между шагами выполняется самим пользователем.
Это не медицинская инструкция и не автоматический контроль позы.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    title: str
    seconds: int
    instruction: str


@dataclass(frozen=True)
class Practice:
    title: str
    steps: tuple[Step, ...]
    caution: str

    @property
    def duration_seconds(self) -> int:
        return sum(step.seconds for step in self.steps)


PRACTICES = {
    "butterfly": Practice(
        title="🦋 Мягкая разминка и Бабочка",
        caution=("Двигайся без боли, не дави на колени и не задерживай дыхание. "
                 "При травмах, боли или ограничениях подвижности проконсультируйся со специалистом. "
                 "Ты можешь пропустить любой шаг."),
        steps=(
            Step("Настройка", 60, "Сядь удобно, проверь опору, спокойно подыши."),
            Step("Плечи и шея", 120, "Мягко подвигай плечами. Без резких движений шеей."),
            Step("Разминка таза", 120, "В комфортной амплитуде подвигай тазом и ногами."),
            Step("Подготовка", 120, "Сядь на опору, согни колени, соедини стопы без усилия."),
            Step("Бабочка", 120, "Держи спину комфортно; колени опускаются только под своим весом."),
            Step("Отдых", 60, "Медленно выпрями ноги и отметь ощущения."),
        ),
    ),
}


def describe(practice: Practice, index: int) -> str:
    step = practice.steps[index]
    total = len(practice.steps)
    minutes, seconds = divmod(step.seconds, 60)
    duration = f"{minutes} мин" if not seconds else f"{minutes} мин {seconds} сек"
    return (f"{practice.title} · этап {index + 1}/{total}\n"
            f"{step.title} — ориентир {duration}\n\n{step.instruction}\n\n"
            "Когда закончишь, отправь «Далее». «Стоп» завершит занятие.")
