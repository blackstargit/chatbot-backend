from fastapi import APIRouter, Path, HTTPException, status
from typing import Dict, Any
from app.types.types import UserChatsResponse

from app.utils.supabase import get_supabase_client, fetch_user_chat_sessions

router = APIRouter()

@router.get(
    "/embed/{embed_id}/user/{client_user_id}/chats",
    response_model=UserChatsResponse,
    summary="List User's Recent Chat Sessions",
    tags=["User Chats"]
)
async def list_user_chats(
    embed_id: str = Path(..., title="The ID of the embed configuration", min_length=1),
    client_user_id: str = Path(..., title="The unique ID of the client user", min_length=1),
    # auth_result: bool = Depends(authenticate_request) # Uncomment if auth is needed
):
    """
    Retrieves a list of recent chat sessions for a specific user associated with an embed.
    The sessions are ordered by the most recent interaction.
    """
    print(f"Received request for /chats: embed_id={embed_id}, client_user_id={client_user_id}")
    
    supabase_client = await get_supabase_client() # Using the utility function

    try:
        chat_sessions_data = await fetch_user_chat_sessions(
            supabase_client, client_user_id, embed_id
        )
        
        return UserChatsResponse(chats=chat_sessions_data)

    except HTTPException:
        raise # Re-raise HTTPExceptions from fetch_user_chat_sessions
    except Exception as e:
        print(f"Unexpected error in list_user_chats endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching chat sessions."
        )