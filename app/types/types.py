from typing import List, Optional
from pydantic import BaseModel, Field
import datetime

# --- Pydantic Models ---
class StreamChatRequest(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    client_user_id: str = Field(..., alias="clientUserId")
    message: str
    prompt: Optional[str] = Field(None, alias="promptOverride")
    model: Optional[str] = Field(None, alias="modelOverride")
    temperature: Optional[float] = Field(None, alias="temperatureOverride")
    username: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str
    uuid: Optional[str] = None

class HistoryResponse(BaseModel):
    history: List[ChatMessage]

class ChatSessionListItem(BaseModel):
    session_id: str
    title: Optional[str] = None
    first_message_preview: Optional[str] = None # Or actual last message content
    last_message_content: Optional[str] = None
    last_message_sender: Optional[str] = None # 'user' or 'assistant'
    last_interacted_at: datetime.datetime # Keep as datetime, frontend can format

    class Config:
        from_attributes = True # For Supabase response conversion if needed


class UserChatsResponse(BaseModel):
    chats: List[ChatSessionListItem]
