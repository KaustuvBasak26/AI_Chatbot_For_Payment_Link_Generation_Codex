import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.routes import chat, health, llm, mock_payments, payment_requests, webhooks
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
cors_origins = [settings.frontend_origin]
if settings.app_env != "production":
    if "localhost" in settings.frontend_origin:
        cors_origins.append(settings.frontend_origin.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in settings.frontend_origin:
        cors_origins.append(settings.frontend_origin.replace("127.0.0.1", "localhost"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=cors_origins, allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-LLM-Provider", "X-LLM-Model", "X-LLM-API-Key", "X-Request-ID", "X-Razorpay-Signature"],
)


@app.middleware("http")
async def correlation_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:100]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details, "request_id": request.state.request_id}})


app.include_router(health.router, prefix="/api/v1")
app.include_router(llm.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(payment_requests.router, prefix="/api/v1")
app.include_router(mock_payments.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
