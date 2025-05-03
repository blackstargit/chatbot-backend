from fastapi import APIRouter, Path, Response, status

from app.types.types import HistoryResponse, ChatMessage
from app.utils.utils import mock_chat_histories

router = APIRouter()

@router.get("/embed/{embed_id}/{session_id}", response_model=HistoryResponse)
async def get_chat_history_mock(
    embed_id: str = Path(..., title="The ID of the embed configuration"),
    session_id: str = Path(..., title="The specific session ID")
):
    print(f"Received get history request for embed_id: {embed_id}, session_id: {session_id}")
    session_history_dicts = mock_chat_histories.get(session_id, [])
    print(f"Found {len(session_history_dicts)} messages in history for session {session_id}")
    session_history_models = [ChatMessage(**msg) for msg in session_history_dicts]
    return HistoryResponse(history=session_history_models)


@router.delete("/embed/{embed_id}/{session_id}", status_code=status.HTTP_200_OK)
async def delete_chat_history_mock(
    embed_id: str = Path(..., title="The ID of the embed configuration"),
    session_id: str = Path(..., title="The specific session ID to delete")
):
    print(f"Received delete history request for embed_id: {embed_id}, session_id: {session_id}")
    removed_history = mock_chat_histories.pop(session_id, None)
    if removed_history is not None:
        print(f"Deleted history for session {session_id}")
    else:
        print(f"No history found to delete for session {session_id}")
    return Response(status_code=status.HTTP_200_OK, content=None)
