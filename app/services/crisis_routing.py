"""Conservative crisis triage for an opt-in support bot.

This is keyword-based routing, not a clinical risk assessment. Never log raw
messages; uncertainty should be handled by offering immediate human support.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CrisisRoute:
    urgent: bool
    response: str
    reason: str


_RU = (
    re.compile(r"хочу\s+(?:покончить\s+с\s+собой|умереть|убить\s+себя)", re.I),
    re.compile(r"(?:планирую|собираюсь)\s+(?:суицид|самоубийство|убить\s+себя)", re.I),
    re.compile(r"(?:сейчас|сегодня)\s+(?:порежу|наврежу)\s+себе", re.I),
)
_EN = (
    re.compile(r"\bi\s+(?:want|plan|intend)\s+to\s+(?:kill\s+myself|end\s+my\s+life|die)\b", re.I),
    re.compile(r"\bi(?:'m| am)\s+going\s+to\s+(?:kill|hurt)\s+myself\b", re.I),
)


def route_crisis(message: str, *, locale: str = "ru") -> CrisisRoute:
    if locale not in {"ru", "en"}:
        raise ValueError("Unsupported locale")
    patterns = _RU if locale == "ru" else _EN
    if not any(pattern.search(message) for pattern in patterns):
        return CrisisRoute(False, "", "no_keyword_match")
    if locale == "ru":
        response = (
            "Мне важно, чтобы ты сейчас был в безопасности. "
            "Если есть непосредственная опасность, позвони в местную экстренную службу "
            "или обратись в ближайшее отделение неотложной помощи. "
            "По возможности отойди от предметов, которыми можно причинить себе вред, "
            "и свяжись с человеком, которому доверяешь, попросив побыть рядом. "
            "Я не могу заменить экстренную помощь. "
            "В какой стране ты находишься? Я помогу найти подходящий контакт."
        )
    else:
        response = (
            "Your immediate safety matters. If you are in immediate danger, "
            "call your local emergency number or go to the nearest emergency department. "
            "If possible, move away from anything you could use to hurt yourself "
            "and ask a trusted person to stay with you. "
            "I cannot replace emergency services. "
            "What country are you in? I can help identify an appropriate contact."
        )
    return CrisisRoute(True, response, "explicit_self_harm_intent")
