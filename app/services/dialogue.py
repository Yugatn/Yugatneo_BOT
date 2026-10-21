from app.core.models import IncomingMessage, OutgoingMessage
from app.llm.factory import get_llm
from app.services.monetization import support_buttons, support_notice
from app.services.diagnostic_flow import adaptive_context, handle_diagnostic_message


async def respond(message: IncomingMessage, conversation_summary: str = "") -> OutgoingMessage:
    text = message.text.strip()
    if not text:
        return OutgoingMessage(text="Напиши сообщение или выбери тему, с которой хочешь начать.")
    if text.lower() in {"/support", "поддержать", "поддержка"}:
        if not support_buttons():
            return OutgoingMessage(text="Добровольная поддержка через Tribute сейчас не включена. Все основные функции остаются бесплатными.")
        return OutgoingMessage(
            text="Поддержка Yugatneo BOT полностью добровольна. Все основные функции остаются бесплатными." + support_notice(),
            buttons=support_buttons(),
        )
    if text.lower() in {"/start", "start", "начать"}:
        return OutgoingMessage(
            text=(
                "Привет! Я Yugatneo BOT — помощник для коучинга, самоисследования и психообразования. "
                "Я не заменяю психотерапевта и не ставлю диагнозы. "
                "Работа добровольная: ты можешь пропустить любой вопрос или остановиться. "
                "Не отправляй пароли, платёжные данные и сведения, которые не хочешь передавать сервису. "
                "Если согласен продолжить в таком формате, напиши «Согласен»; если нет — можешь завершить диалог."
                + support_notice()
            ),
            buttons=[
                {"label": "Согласен, продолжить", "value": "согласен"},
                {"label": "Начать без анкеты", "value": "пропустить диагностику"},
            ] + support_buttons(),
        )
    flow = handle_diagnostic_message(message.channel.value, message.external_user_id, text)
    if flow is not None:
        return OutgoingMessage(
            text=flow["text"],
            buttons=flow.get("buttons", []),
            metadata={key: str(value) for key, value in flow.get("metadata", {}).items()},
        )
    diagnostic_context = adaptive_context(message.channel.value, message.external_user_id, text)
    combined_summary = "\n".join(part for part in (conversation_summary, diagnostic_context) if part)
    llm = get_llm()
    reply = await llm.generate_reply(user_text=text, conversation_summary=combined_summary)
    return OutgoingMessage(text=reply)
