import os
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from app.utils.lead_capture import _detect_emails, _detect_phones, _detect_names
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any

# Load environment variables
load_dotenv()

# Supabase configuration
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# # Global client instance for synchronous operations
# supabase: Client = create_client(supabase_url, supabase_key)

# Table names
CHAT_HISTORY_TABLE = "chat_histories"
LEAD_CAPTURE_TABLE = "lead_capture_form"
USER_CHATS_TABLE = "user_chats" # Define the new table name

async def get_supabase_client() -> Client:
    """
    Get a Supabase client instance for async operations.
    
    Returns:
        A Supabase client instance
    """
    return create_client(supabase_url, supabase_key)

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
    
    data = {
        "session_id": session_id,
        "role": message["role"],
        "content": message["content"],
        "uuid": message["uuid"]
    }

    supabase: Client = get_supabase_client()
    
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
    
    if not result.data or len(result.data) == 0:
        error_msg = f"Failed to save/update message to Supabase. UUID: {message.get('uuid')}, Session: {session_id}."
        if hasattr(result, 'error') and result.error:
            error_msg += f" Supabase Error: {result.error.message} (Code: {result.error.code})"
        print(error_msg) # Log the error
        raise Exception(error_msg) # Raise an exception to be handled by the caller
      
    
    # --- Lead Capture Logic ---
    if message["role"] == "user" and message.get("content"): # Only process user messages with content
        user_content = str(message["content"])

        emails = _detect_emails(user_content)
        phones = _detect_phones(user_content)
        names = _detect_names(user_content)

        detected_email = ", ".join(emails) if emails else None
        detected_phone = ", ".join(phones) if phones else None
        detected_name = ", ".join(names) if names else None 
        
        if detected_email or detected_phone or detected_name:
            print(f"Lead info found in message {message['uuid']}: Name='{detected_name}', Email='{detected_email}', Phone='{detected_phone}'")
            try:
                await _save_detected_lead_info(
                    supabase,
                    session_id,
                    message["uuid"],
                    detected_name,
                    detected_email,
                    detected_phone,
                    user_content
                )
            except Exception as e_lead_capture:
                print(f"Error during lead capture for message UUID {message['uuid']}: {e_lead_capture}")
    
    return result.data[0]


async def ensure_user_chat_record(
    supabase_client: Client, # Expecting an already initialized client
    client_user_id: str,
    embed_id: str,
    session_id: str,
    first_message_content: Optional[str] = None,
    message_timestamp: Optional[str] = None  # ISO format timestamp string for created_at and last_interacted_at
) -> None:
    """
    Ensures a record exists in user_chats for the given user, embed, and session.
    If it doesn't exist, it creates one.
    This should ideally be called when the first user message of a session is processed.
    """
    print(f"Ensuring user_chat record for client_user_id: {client_user_id}, embed_id: {embed_id}, session_id: {session_id}")

    # Check if a record already exists to avoid unnecessary ON CONFLICT write attempts
    # and to handle the logic more explicitly.
    existing_check_result = await supabase_client.table(USER_CHATS_TABLE) \
        .select("id") \
        .eq("client_user_id", client_user_id) \
        .eq("embed_id", embed_id) \
        .eq("session_id", session_id) \
        .limit(1) \
        .execute()

    if existing_check_result.data:
        print(f"User_chat record already exists for session_id {session_id} (client: {client_user_id}, embed: {embed_id}).")
        # The trigger on chat_histories will update last_interacted_at.
        return

    # If no record, create it
    print(f"Creating new user_chat record for session_id {session_id} (client: {client_user_id}, embed: {embed_id}).")
    
    preview = None
    if first_message_content:
        preview = (first_message_content[:97] + '...') if len(first_message_content) > 100 else first_message_content

    insert_data = {
        "client_user_id": client_user_id,
        "embed_id": embed_id,
        "session_id": session_id,
        "first_message_preview": preview
    }
    
    # If message_timestamp (from the first user message in chat_histories) is provided, use it.
    # Otherwise, DB defaults (NOW()) will apply for created_at and last_interacted_at.
    if message_timestamp:
        insert_data["created_at"] = message_timestamp
        insert_data["last_interacted_at"] = message_timestamp
    
    try:
        # The unique constraint on (client_user_id, embed_id, session_id) will prevent duplicates.
        result = await supabase_client.table(USER_CHATS_TABLE).insert(insert_data).execute()

        if result.data and len(result.data) > 0:
            print(f"Successfully created user_chat record with ID: {result.data[0].get('id')}")
        elif hasattr(result, 'error') and result.error:
            # Check if the error is due to a unique constraint violation (code '23505' for PostgreSQL)
            if hasattr(result.error, 'code') and result.error.code == '23505':
                print(f"User_chat record for session_id {session_id} likely created by a concurrent request (unique constraint violation). Assuming it exists.")
            else:
                print(f"Error creating user_chat record for session_id {session_id}: {result.error.message} (Code: {result.error.code if hasattr(result.error, 'code') else 'N/A'})")
                # Optionally re-raise or handle other errors specifically
        else:
            print(f"Unknown issue creating user_chat record for session_id {session_id}. No data returned and no explicit error.")

    except Exception as e:
        # Catch any other exceptions during the insert operation
        print(f"Exception during user_chat insert for session_id {session_id}: {str(e)}")
        # Check if it's a known unique violation from a different driver or ORM exception type
        if "unique constraint" in str(e).lower(): # Generic check for unique constraint error text
            print(f"User_chat record for session_id {session_id} likely created by a concurrent request (caught generic unique constraint exception). Assuming it exists.")
        else:
            raise # Re-raise other unexpected errors

async def fetch_user_chat_sessions(
    supabase_client: Client, # Using Any for Supabase client type, replace with actual if available
    client_user_id: str,
    embed_id: str,
    limit: int = 20, # Default limit for pagination
    offset: int = 0  # Default offset for pagination
) -> List[Dict[str, Any]]:
    """
    Fetches chat sessions for a given user and embed, ordered by last interaction.
    Includes the content and role of the last message in each session.
    """
    try:
        user_chats_response = await supabase_client.table("user_chats") \
            .select("session_id, title, first_message_preview, last_interacted_at") \
            .eq("client_user_id", client_user_id) \
            .eq("embed_id", embed_id) \
            .order("last_interacted_at", desc=True) \
            .limit(limit) \
            .offset(offset) \
            .execute()

        if user_chats_response.data is None:
            print(f"No user_chats data found for client {client_user_id}, embed {embed_id}")
            return []

        sessions_data = []
        for chat in user_chats_response.data:
            last_message_response = await supabase_client.table("chat_histories") \
                .select("content, role") \
                .eq("session_id", chat["session_id"]) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            last_message_content = None
            last_message_sender = None
            if last_message_response.data:
                last_message_content = last_message_response.data[0]["content"]
                last_message_sender = last_message_response.data[0]["role"]
            
            sessions_data.append({
                "session_id": chat["session_id"],
                "title": chat["title"],
                "first_message_preview": chat["first_message_preview"],
                "last_interacted_at": chat["last_interacted_at"],
                "last_message_content": last_message_content,
                "last_message_sender": last_message_sender
            })
        
        print(f"Fetched {len(sessions_data)} chat sessions for client_user_id: {client_user_id}, embed_id: {embed_id}")
        return sessions_data

    except Exception as e:
        print(f"Error fetching user chat sessions for client {client_user_id}, embed {embed_id}: {str(e)}")
        # Log the full error for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat sessions."
        )


async def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a session from Supabase
    
    Args:
        session_id: The session ID
        
    Returns:
        List of messages for the session
    """
    supabase: Client = get_supabase_client()

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
    supabase: Client = get_supabase_client()

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

async def _save_detected_lead_info(
    supabase_client: Client,
    session_id: str,
    message_uuid: str,
    detected_name: Optional[str],
    detected_email: Optional[str],
    detected_phone: Optional[str],
    original_content: str
) -> None:
    """Saves detected lead information to the Supabase lead_capture_form table."""
    
    if not (detected_name or detected_email or detected_phone):
        # print(f"No lead info detected for message {message_uuid}")
        return 

    lead_data = {
        "chat_message_uuid": message_uuid,
        "session_id": session_id,
        "detected_name": detected_name,
        "detected_email": detected_email,
        "detected_phone": detected_phone,
        "original_message_content": original_content,
    }

    try:
        result = await supabase_client.table(LEAD_CAPTURE_TABLE).insert(lead_data).execute()
        if result.data and len(result.data) > 0:
            print(f"Successfully saved lead with ID: {result.data[0].get('id')} for message {message_uuid}")
    except Exception as e:
        if "unique constraint" in str(e).lower() or (hasattr(e, 'code') and e.code == '23505'): # PostgreSQL unique violation
            print(f"Lead for message UUID {message_uuid} already exists. Skipping insert.")
        else:
            print(f"An error occurred while saving lead information for message {message_uuid}: {e}")