import os
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Global client instance for synchronous operations
supabase: Client = create_client(supabase_url, supabase_key)

# Table names
CHAT_HISTORY_TABLE = "chat_histories"
LEAD_CAPTURE_TABLE = "lead_capture_form"

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
                    supabase_client,
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

async def _save_detected_lead_info(
    supabase_client: Any,
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