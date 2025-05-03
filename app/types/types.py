from typing import List, Optional
from pydantic import BaseModel, Field

# --- Pydantic Models ---
class StreamChatRequest(BaseModel):
    session_id: str = Field(..., alias="sessionId")
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
