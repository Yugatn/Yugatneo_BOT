import asyncio
from app.core.models import Channel, IncomingMessage
from app.services.dialogue import respond


def test_start_gives_intro():
    message = IncomingMessage(channel=Channel.WEB, external_user_id="test-user", text="/start")
    reply = asyncio.run(respond(message))
    assert "не заменяю психотерапевта" in reply.text
    assert len(reply.buttons) > 0


def test_empty_message_prompts_user():
    message = IncomingMessage(channel=Channel.WEB, external_user_id="test-user", text="  ")
    reply = asyncio.run(respond(message))
    assert "Напиши сообщение" in reply.text
