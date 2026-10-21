from app.core.models import IncomingMessage, OutgoingMessage
from app.llm.factory import get_llm


async def respond(message: IncomingMessage, conversation_summary: str = "") -> OutgoingMessage:
    text = message.text.strip()
    if not text:
        return OutgoingMessage(text="Напиши сообщение или выбери тему, с которой хочешь начать.")
    if text.lower() in {"/start", "start", "начать"}:
        return OutgoingMessage(
            text=(
                "Привет! Я Yugatneo BOT — помощник для коучинга, самоисследования и психообразования. "
                "Я не заменяю психотерапевта и не ставлю диагнозы. "
                "Работа добровольная: ты можешь пропустить любой вопрос или остановиться. "
                "Не отправляй пароли, платёжные данные и сведения, которые не хочешь передавать сервису. "
                "Если согласен продолжить в таком формате, напиши «Согласен»; если нет — можешь завершить диалог."
            ),
            buttons=[
                {"label": "Эмоции и состояние", "value": "topic:emotions"},
                {"label": "Цели и решения", "value": "topic:goals"},
                {"label": "Отношения", "value": "topic:relationships"},
            ],
        )
    llm = get_llm()
    reply = await llm.generate_reply(user_text=text, conversation_summary=conversation_summary)
    return OutgoingMessage(text=reply)
