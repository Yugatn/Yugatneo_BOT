"""Conservative crisis-message triage for the dialogue MVP.

This is a keyword-based safety net, not a risk assessment or clinical classifier.
It deliberately prefers a supportive hand-off over attempting therapy in a crisis.
"""
from __future__ import annotations

import re

_IMMEDIATE_PATTERNS = (
    r"\b(сейчас|сегодня|прямо сейчас)\b.{0,50}\b(покончить с собой|убить себя|совершить самоубийство)\b",
    r"\b(собираюсь|решил|решила|намерен|намерена)\b.{0,40}\b(убить себя|покончить с собой|совершить самоубийство)\b",
    r"\b(уже|только что)\b.{0,35}\b(принял|приняла|выпил|выпила)\b.{0,30}\b(таблетк|яд|лекарств)\w*",
    r"\b(i am going to|i will|about to)\b.{0,35}\b(kill myself|end my life|commit suicide)\b",
    r"\b(i already took)\b.{0,35}\b(pills|overdose|poison)\b",
)
_CONCERN_PATTERNS = (
    r"\b(не хочу жить|не хочется жить|хочу умереть|лучше бы меня не было|думаю о самоубийстве|мысли о самоубийстве|суицидальн\w* мысли)\b",
    r"\b(i want to die|i don't want to live|i do not want to live|suicidal thoughts|thinking about suicide)\b",
)
_NEGATED_OR_FICTION_CONTEXT = (
    "не собираюсь причинять себе вред",
    "не хочу причинять себе вред",
    "нет мыслей о самоубийстве",
    "в романе",
    "в книге",
    "персонаж",
    "для сценария",
)


def classify_crisis_message(text: str) -> str | None:
    """Return 'immediate' or 'concern', or None. Never interpret as a diagnosis."""
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    # Explicit near-term intent or a reported attempt takes precedence over contextual words.
    if any(re.search(pattern, normalized) for pattern in _IMMEDIATE_PATTERNS):
        return "immediate"
    if any(phrase in normalized for phrase in _NEGATED_OR_FICTION_CONTEXT):
        return None
    if any(re.search(pattern, normalized) for pattern in _CONCERN_PATTERNS):
        return "concern"
    return None


def crisis_response(level: str) -> str:
    """A localized-neutral response that does not assume the user's country."""
    if level == "immediate":
        return (
            "Мне очень жаль, что тебе сейчас настолько тяжело. Сейчас важнее всего физическая безопасность. "
            "Если ты уже причинил(а) себе вред, принял(а) опасное количество лекарства или можешь сделать это в ближайшее время, "
            "немедленно позвони в местную экстренную службу или попроси человека рядом вызвать помощь. "
            "Перейди туда, где есть другие люди, и скажи доверенному человеку прямо: «Мне сейчас небезопасно оставаться одному/одной; побудь со мной и помоги вызвать помощь». "
            "Если можешь сделать это безопасно, отойди от предметов и веществ, которыми можно навредить себе. "
            "Я могу оставаться с тобой в разговоре, но не могу заменить экстренную помощь. "
            "Ты уже причинил(а) себе вред или находишься в непосредственной опасности прямо сейчас?"
        )
    return (
        "Спасибо, что сказал(а) об этом. Мне жаль, что тебе приходится через это проходить. "
        "Я не буду делать выводы о тебе по одному сообщению, и тебе не нужно справляться с этим в одиночку. "
        "Хочу сначала уточнить безопасность: есть ли у тебя намерение причинить себе вред прямо сейчас или конкретный план на ближайшее время? "
        "Если да или ты не уверен(а), что сможешь оставаться в безопасности, свяжись с местной экстренной службой, кризисной линией или человеком, который может побыть рядом. "
        "Если непосредственной опасности нет, мы можем спокойно обсудить, что происходит, а также найти живую профессиональную поддержку."
    )
