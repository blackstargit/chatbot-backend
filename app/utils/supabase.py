import os
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(supabase_url, supabase_key)

# Table name for chat history
CHAT_HISTORY_TABLE = "chat_histories"

async def save_message(session_id: str, message: Dict[str, Any], update: bool = False) -> Dict[str, Any]:
    """
    Save a message to the chat history in Supabase
    
    Args:
        session_id: The session ID
        message: The message to save
        update: If True, update an existing message instead of inserting a new one
        
    Returns:
        The saved message with Supabase metadata
    """
    
    # Add session_id to the message data
    data = {
        "session_id": session_id,
        "role": message["role"],
        "content": message["content"],
        "uuid": message["uuid"]
    }
    
    if update:
        # Update the existing message with the same UUID
        result = supabase.table(CHAT_HISTORY_TABLE)\
            .update(data)\
            .eq("session_id", session_id)\
            .eq("uuid", message["uuid"])\
            .execute()
    else:
        # Insert a new message
        result = supabase.table(CHAT_HISTORY_TABLE).insert(data).execute()
    
    if len(result.data) == 0:
        raise Exception("Failed to save message to Supabase")
        
    return result.data[0]

async def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a session from Supabase
    
    Args:
        session_id: The session ID
        
    Returns:
        List of messages for the session
    """
    result = supabase.table(CHAT_HISTORY_TABLE) \
        .select("*") \
        .eq("session_id", session_id) \
        .order("created_at") \
        .execute()
        
    # Transform the data to match the expected format
    messages = []
    for item in result.data:
        messages.append({
            "role": item["role"],
            "content": item["content"],
            "uuid": item["uuid"]
        })
        
    return messages

async def delete_session_history(session_id: str) -> bool:
    """
    Delete all messages for a session from Supabase
    
    Args:
        session_id: The session ID
        
    Returns:
        True if messages were deleted, False if no messages were found
    """
    # First check if there are any messages for this session
    count_result = supabase.table(CHAT_HISTORY_TABLE) \
        .select("*", count="exact") \
        .eq("session_id", session_id) \
        .execute()
        
    if count_result.count == 0:
        return False
        
    # Delete all messages for the session
    supabase.table(CHAT_HISTORY_TABLE) \
        .delete() \
        .eq("session_id", session_id) \
        .execute()
        
    return True
