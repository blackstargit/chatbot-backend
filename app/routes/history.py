from fastapi import APIRouter, Path, Response, status, Request, BackgroundTasks, Depends

from app.types.types import HistoryResponse, ChatMessage
from app.utils.supabase import get_session_history, delete_session_history
from app.utils.utils import process_frontend_url
from app.utils.auth import authenticate_request

router = APIRouter()

@router.get("/embed/{embed_id}/{session_id}", response_model=HistoryResponse)
async def get_chat_history(
    request: Request,
    background_tasks: BackgroundTasks,
    embed_id: str = Path(..., title="The ID of the embed configuration"),
    session_id: str = Path(..., title="The specific session ID"),
    # _auth: bool = Depends(authenticate_request)
):
    frontend_url = request.headers.get("origin") or request.headers.get("referer")
    print(f"Received get history request for embed_id: {embed_id}, session_id: {session_id} from {frontend_url}")
    
    # Process the frontend URL in the background
    if frontend_url:
        background_tasks.add_task(process_frontend_url, request.app, frontend_url)

    # Get session history from Supabase
    session_history_dicts = await get_session_history(session_id)
    print(f"Found {len(session_history_dicts)} messages in history for session {session_id}")
    
    # Convert to Pydantic models
    session_history_models = [ChatMessage(**msg) for msg in session_history_dicts]
    return HistoryResponse(history=session_history_models)


@router.delete("/embed/{embed_id}/{session_id}", status_code=status.HTTP_200_OK)
async def delete_chat_history(
    embed_id: str = Path(..., title="The ID of the embed configuration"),
    session_id: str = Path(..., title="The specific session ID to delete"),
    # _auth: bool = Depends(authenticate_request)
):
    print(f"Received delete history request for embed_id: {embed_id}, session_id: {session_id}")
    
    # Delete session history from Supabase
    deleted = await delete_session_history(session_id)
    
    if deleted:
        print(f"Deleted history for session {session_id}")
    else:
        print(f"No history found to delete for session {session_id}")
        
    return Response(status_code=status.HTTP_200_OK, content=None)
