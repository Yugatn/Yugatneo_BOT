from fastapi import FastAPI, HTTPException, Request
from app.miniapp_wheel_api import router as miniapp_wheel_router
from app.miniapp_coaching_api import router as miniapp_coaching_router
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pathlib import Path
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.core.models import IncomingMessage, OutgoingMessage
from app.services.dialogue import respond
from app.services.access_store import claim_question
from app.services.catalog import get_question, load_questions
from app.services.security import allow_request
from app.services.miniapp_cors import (
    is_coaching_route, trusted_origins, allowed_headers, preflight_headers,
)
from app.services.human_gate import verify_turnstile_and_issue_code
from app.services.diagnostic import DiagnosticProfile, prioritize_questions

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.5.0",
    docs_url=None if settings.app_env.lower() == "production" else "/docs",
    redoc_url=None,
)


app.include_router(miniapp_wheel_router)
app.include_router(miniapp_coaching_router)

class HumanVerificationRequest(BaseModel):
    ticket: str = Field(min_length=1, max_length=4096)
    signature: str = Field(min_length=1, max_length=256)
    turnstile_token: str = Field(min_length=1, max_length=4096)


class DiagnosticRequest(BaseModel):
    age: int = Field(ge=1, le=120)
    gender: str | None = Field(default=None, max_length=80)
    temperament: str = Field(default="unsure", max_length=32)
    psychotype: str = Field(default="unsure", max_length=80)
    goal: str = Field(default="general", max_length=32)
    distress: int = Field(default=1, ge=0, le=4)
    urgency: str = Field(default="normal", max_length=16)
    style: str = Field(default="unsure", max_length=32)
    limit: int = Field(default=12, ge=1, le=30)


@app.middleware("http")
async def security_baseline(request: Request, call_next):
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > 32_000:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
    client_host = request.client.host if request.client else "unknown"
    if not allow_request(f"ip:{client_host}", limit=120, window_seconds=60):
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
    coaching_cors = None
    if is_coaching_route(request.url.path):
        origin = request.headers.get("origin")
        allowed = trusted_origins(settings.miniapp_coaching_allowed_origins)
        if origin is not None:
            coaching_cors = allowed_headers(origin, allowed)
            if coaching_cors is None:
                return JSONResponse(
                    status_code=403, content={"detail": "Untrusted Mini App origin"},
                    headers={"Cache-Control": "no-store", "Vary": "Origin"},
                )
        if request.method == "OPTIONS":
            preflight = preflight_headers(
                origin or "", request.headers.get("access-control-request-method", ""),
                request.headers.get("access-control-request-headers", ""), allowed,
            )
            if preflight is None:
                return Response(status_code=403, headers={"Cache-Control": "no-store", "Vary": "Origin"})
            return Response(status_code=204, headers=preflight)
    response = await call_next(request)
    if coaching_cors is not None:
        response.headers.update(coaching_cors)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    if settings.app_env.lower() == "production":
        if request.url.path == "/human/check":
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'self' https://challenges.cloudflare.com; "
                "frame-src https://challenges.cloudflare.com; connect-src 'self'; "
                "style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


@app.get("/human/check", response_class=HTMLResponse)
async def human_check():
    if not settings.turnstile_site_key:
        raise HTTPException(status_code=503, detail="Human verification is not configured")
    page = (Path(__file__).resolve().parents[1] / "web" / "human-check.html").read_text(encoding="utf-8")
    page = page.replace("__TURNSTILE_SITE_KEY__", settings.turnstile_site_key)
    return HTMLResponse(page)


@app.post("/human/verify")
async def human_verify(body: HumanVerificationRequest, request: Request):
    """Verify Cloudflare Turnstile for a short-lived ticket issued by a trusted channel adapter.

    On success the user must send the returned one-time code to the same bot account.
    Do not expose ticket creation based on arbitrary client-supplied user IDs.
    """
    if not settings.ticket_signing_secret or not settings.turnstile_secret_key:
        raise HTTPException(status_code=503, detail="Human verification is not configured")
    host = request.client.host if request.client else None
    if not allow_request(f"captcha:{host or 'unknown'}", limit=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many verification attempts")
    try:
        code = await verify_turnstile_and_issue_code(
            body.ticket, body.signature, body.turnstile_token, host
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Human verification service unavailable") from exc
    return {
        "status": "verification_passed",
        "one_time_code": code,
        "expires_in_seconds": 300,
        "next_step": "Send this code to the same bot account that opened the verification link.",
    }


@app.post("/diagnostic/recommend")
async def diagnostic_recommend(profile: DiagnosticRequest):
    """Suggest an order for reflective questions. No profile is persisted by this endpoint."""
    try:
        result = prioritize_questions(
            load_questions(),
            DiagnosticProfile(
                age=profile.age,
                gender=profile.gender,
                temperament=profile.temperament,
                psychotype=profile.psychotype,
                goal=profile.goal,
                distress=profile.distress,
                urgency=profile.urgency,
                style=profile.style,
            ),
            limit=profile.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@app.get("/dev/catalog")
async def dev_catalog():
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    questions = load_questions()
    return {"count": len(questions), "categories": sorted({q.category for q in questions})}


@app.post("/dev/question", response_model=OutgoingMessage)
async def dev_question(message: IncomingMessage) -> OutgoingMessage:
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    subject = f"user:{message.channel.value}:{message.external_user_id}"
    if not allow_request(subject, limit=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests for this user")
    decision = claim_question(
        message.channel.value,
        message.external_user_id,
        free_limit=settings.free_question_limit,
    )
    question = get_question(decision["question_index"])
    return OutgoingMessage(
        text=question.text,
        buttons=[{"label": "Пропустить вопрос", "value": "question:skip"}],
        metadata={
            "access": decision["reason"],
            "access_policy": "unlimited_free",
            "question_id": question.id,
            "category": question.category,
        },
    )


@app.post("/dev/message", response_model=OutgoingMessage)
async def dev_message(message: IncomingMessage) -> OutgoingMessage:
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    subject = f"user:{message.channel.value}:{message.external_user_id}"
    if not allow_request(subject, limit=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests for this user")
    return await respond(message)
