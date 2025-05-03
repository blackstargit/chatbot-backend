from fastapi import APIRouter, Path, Response, status, Request

from app.types.types import HistoryResponse, ChatMessage
from app.utils.supabase import get_session_history, delete_session_history

router = APIRouter()

@router.get("/widget-snippet")
def widget_snippet():
    js = '<script src="https://cdn.example.com/widget.js" defer></script>'
    return Response(content=js, media_type="text/plain")