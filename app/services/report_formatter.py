"""Format self-reflection reports without inferring psychological diagnoses."""
from __future__ import annotations


def build_report(locale: str, scores: list[tuple[str, int]],
                 career: tuple[str, str, str] | None,
                 active: tuple[str, str] | None,
                 completed: list[tuple[str, str, str]]) -> str:
    en = locale == "en"
    if not any((scores, career, active, completed)):
        return ("No saved information yet. Start with /wheel or /career."
                if en else "Пока нет сохранённых данных. Начни с /wheel или /career.")
    lines = [
        "📄 YOUR SELF-REFLECTION REPORT" if en else "📄 ТВОЙ ОТЧЁТ О САМООЦЕНКЕ",
        ("This summarizes your own entries; it is not a psychological diagnosis."
         if en else "Это сводка твоих записей, а не психологический диагноз."),
    ]
    if scores:
        lines.append("\nCurrent ratings:" if en else "\nТекущие оценки:")
        lines.extend(f"• {name}: {score}/10" for name, score in scores)
        avg = sum(score for _, score in scores) / len(scores)
        lines.append(
            (f"Average across rated areas: {avg:.1f}/10 (descriptive only, not a mental-health score)."
             if en else f"Среднее по оценённым сферам: {avg:.1f}/10 (описательная величина, не показатель психического здоровья).")
        )
    if career:
        lines.append("\nInterests and skills:" if en else "\nИнтересы и навыки:")
        for en_label, ru_label, value in zip(
            ("Interest", "Skill or experience", "Experiment"),
            ("Интерес", "Навык или опыт", "Эксперимент"), career
        ):
            lines.append(f"• {en_label if en else ru_label}: {value}")
    if active:
        lines.append((f"\nChosen action: {active[0]} — {active[1]}"
                      if en else f"\nВыбранное действие: {active[0]} — {active[1]}"))
    if completed:
        lines.append("\nRecently completed:" if en else "\nНедавние достижения:")
        lines.extend(f"• {sphere}: {action} ({date})" for sphere, action, date in completed)
    lines.append(
        "\nYou can revisit your ratings, choose a small action or explore another exercise."
        if en else "\nМожешь пересмотреть оценки, выбрать небольшой шаг или другое упражнение."
    )
    return "\n".join(lines)
