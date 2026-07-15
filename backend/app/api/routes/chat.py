from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import llm_headers
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=ChatResponse)
async def send_message(data: ChatRequest, headers: Annotated[tuple[str | None, str | None, object | None], Depends(llm_headers)], db: Session = Depends(get_db)) -> ChatResponse:
    _, model, key = headers
    return await ChatService(db, get_settings()).handle(data, key, model)  # type: ignore[arg-type]

