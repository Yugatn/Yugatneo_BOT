from fastapi import FastAPI, HTTPException
from app.core.config import get_settings
from app.core.models import IncomingMessage, OutgoingMessage
from app.services.dialogue import respond
from app.services.access_store import claim_question
from app.services.catalog import get_question, load_questions

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


@app.get("/dev/catalog")
async def dev_catalog():
    """Development endpoint exposing catalog metadata only; disable in production."""
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    questions = load_questions()
    return {"count": len(questions), "categories": sorted({q.category for q in questions})}


@app.post("/dev/question", response_model=OutgoingMessage)
async def dev_question(message: IncomingMessage) -> OutgoingMessage:
    """Development-only endpoint for the next catalogue question and free-limit gate."""
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    decision = claim_question(
        message.channel.value,
        message.external_user_id,
        free_limit=settings.free_question_limit,
    )
    if not decision["allowed"]:
        return OutgoingMessage(
            text=(
                "Ты использовал(а) семь бесплатных вопросов из каталога. "
                "Чтобы продолжить работу с библиотекой вопросов, нужна активная подписка. "
                "Подписка пока не подключена в этой версии; платёж не принимай и данные карты не отправляй."
            ),
            buttons=[{"label": "О подписке", "value": "subscription:info"}],
            metadata={"access": "subscription_required"},
        )
    question = get_question(decision["question_index"])
    return OutgoingMessage(
        text=question.text,
        buttons=[{"label": "Пропустить вопрос", "value": "question:skip"}],
        metadata={
            "access": decision["reason"],
            "remaining_free": str(decision["remaining_free"]),
            "question_id": question.id,
            "category": question.category,
        },
    )


@app.post("/dev/message", response_model=OutgoingMessage)
async def dev_message(message: IncomingMessage) -> OutgoingMessage:
    """Development-only chat endpoint. Protect or remove before public deployment."""
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    return await respond(message)
