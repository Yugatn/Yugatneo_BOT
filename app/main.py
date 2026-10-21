from fastapi import FastAPI
from app.core.config import get_settings
from app.core.models import IncomingMessage, OutgoingMessage
from app.services.dialogue import respond

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


@app.post("/dev/message", response_model=OutgoingMessage)
async def dev_message(message: IncomingMessage) -> OutgoingMessage:
    """Development-only endpoint. Protect or remove before public deployment."""
    if settings.app_env.lower() == "production":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return await respond(message)
