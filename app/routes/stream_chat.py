import asyncio
import json
import uuid
import random
from typing import Dict, Any
from fastapi import APIRouter, Path, Body, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.types.types import StreamChatRequest
from app.utils.utils import format_sse_chunk, mock_chat_histories

router = APIRouter()

@router.post("/embed/{embed_id}/stream-chat")
async def stream_chat_mock_aligned(
    embed_id: str = Path(..., title="The ID of the embed configuration"),
    raw_body: str = Body(...)
):
    request_uuid = str(uuid.uuid4()) + "1fd" # Unique ID for this request handling instance
    print(f"Request ID: {request_uuid}")
    print(f"Received stream-chat request for embed_id: {embed_id}")
    print(f"Raw request body received: {raw_body}")

    try:
        data_dict = json.loads(raw_body)
        request_data = StreamChatRequest.model_validate(data_dict)
        print(f"Successfully parsed and validated request body from string.")
        print(f"Validated data: {request_data.model_dump(exclude_unset=True)}")
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON from raw body string.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON string in request body.")
    except ValidationError as e:
        print(f"Error: Validation failed after parsing JSON string: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())

    session_id = request_data.session_id
    user_message_text = request_data.message

    user_message_uuid = str(uuid.uuid4())
    user_message_entry = {"role": "user", "content": user_message_text, "uuid": user_message_uuid}
    mock_chat_histories[session_id].append(user_message_entry)
    print(f"Saved user message for session {session_id} with UUID: {user_message_uuid}")

    # --- Simulate Backend Logic & Determine Response ---
    mock_chat_mode = random.choice(["query", "chat"])
    mock_streaming_enabled = random.choice([True, False])
    mock_has_embeddings = random.choice([True, True, False])
    mock_workspace_slug = f"ws_{embed_id}"
    print(f"Simulating: chat_mode='{mock_chat_mode}', streaming={mock_streaming_enabled}, has_embeddings={mock_has_embeddings}")

    assistant_response_text = None
    early_exit_data = None # Store data for early exit chunks
    mock_sources = []

    # Handle Early Exits
    if mock_chat_mode == "query" and not mock_has_embeddings:
        print("Simulating empty workspace in query mode exit.")
        early_exit_data = {
            "uuid": str(uuid.uuid4()),
            "type": "textResponse",
            "textResponse": "I don't have any data to work with. Please add documents to this workspace.",
            "sources": [],
            "close": True,
            "error": False
        }
    elif mock_chat_mode == "query" and "help" in user_message_text.lower():
        print("Simulating help request in query mode exit.")
        early_exit_data = {
            "uuid": str(uuid.uuid4()),
            "type": "textResponse",
            "textResponse": "I'm here to help answer questions about your documents. What would you like to know?",
            "sources": [],
            "close": True,
            "error": False
        }
    elif mock_chat_mode == "query" and "error" in user_message_text.lower():
        print("Simulating error in query mode exit.")
        early_exit_data = {
            "uuid": str(uuid.uuid4()),
            "type": "textResponse",
            "textResponse": None,
            "sources": [],
            "close": True,
            "error": True,
            "errorMessage": "An error occurred while processing your request."
        }
    
    # If we have early exit data, return it as a non-streaming response
    if early_exit_data:
        assistant_message_uuid = early_exit_data["uuid"]
        assistant_message_text = early_exit_data.get("textResponse", "")
        
        # If there's a valid text response, save it to history
        if assistant_message_text:
            assistant_message_entry = {"role": "assistant", "content": assistant_message_text, "uuid": assistant_message_uuid}
            mock_chat_histories[session_id].append(assistant_message_entry)
            print(f"Saved assistant response for session {session_id} (early exit) with UUID: {assistant_message_uuid}")
        
        # Return a single SSE chunk with the early exit data
        async def early_exit_generator():
            yield format_sse_chunk(early_exit_data)
        
        return StreamingResponse(early_exit_generator(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
        })
    
    # --- Main Chat Flow ---
    # Generate a mock response
    if "document" in user_message_text.lower() or "pdf" in user_message_text.lower():
        assistant_response_text = "I found several documents in the workspace. The main topics include project planning, technical specifications, and user feedback. Would you like me to summarize any specific document?"
        # Add mock sources for document-related queries
        mock_sources = [
            {"text": "Project planning document outlines timeline and milestones.", "title": "Project_Plan.pdf", "url": None},
            {"text": "Technical specifications detail system architecture and components.", "title": "Tech_Specs.docx", "url": None}
        ]
    elif "help" in user_message_text.lower():
        assistant_response_text = "I'm an AI assistant designed to help with your questions. I can provide information, assist with tasks, or engage in conversation. How can I help you today?"
    elif "weather" in user_message_text.lower():
        assistant_response_text = "I don't have access to real-time weather data. You might want to check a weather service or website for the most current information."
    elif "hello" in user_message_text.lower() or "hi" in user_message_text.lower():
        assistant_response_text = "Hello! How can I assist you today? I'm ready to help with any questions you might have."
    else:
        # Default response for other queries
        assistant_response_text = "I understand you're asking about " + user_message_text[:20] + "... This is a simulated response as I'm operating in mock mode. In a real environment, I would provide relevant information based on your query and available knowledge."
    
    # Create a UUID for the assistant message
    assistant_message_uuid = str(uuid.uuid4())
    
    # Save the assistant message to history
    assistant_message_entry = {"role": "assistant", "content": assistant_response_text, "uuid": assistant_message_uuid}
    mock_chat_histories[session_id].append(assistant_message_entry)
    print(f"Saved assistant response for session {session_id} (streaming) with UUID: {assistant_message_uuid}")

    # Define the generator for streaming
    async def mock_stream_generator_aligned():
        # 1. Start chunk - use the same UUID as the assistant message for consistency
        start_data = {"uuid": assistant_message_uuid, "type": "start", "error": False, "sources": [], "textResponse": None, "close": False}
        yield format_sse_chunk(start_data)
        await asyncio.sleep(0.2)

        # 2. Text chunks
        words = assistant_response_text.split()
        for i, word in enumerate(words):
            text_chunk_data = {
                "uuid": assistant_message_uuid, # Use the same UUID as the assistant message for consistency
                "type": "textResponseChunk",
                "textResponse": f"{word} " if i < len(words) - 1 else word,
                "sources": [], # Sources usually sent at end
                "close": False,
                "error": False, # Explicitly false
            }
            yield format_sse_chunk(text_chunk_data)
            await asyncio.sleep(0.08)

        # 3. Complete chunk
        complete_data = {
            "uuid": assistant_message_uuid, # Use the same UUID as the assistant message for consistency
            "type": "complete", # Use 'complete' type for stream end
            "textResponse": None, # No specific text for complete chunk
            "sources": mock_sources,
            "close": True,
            "error": False, # Explicitly false
        }
        yield format_sse_chunk(complete_data)
        print(f"Finished streaming mock response for embed_id: {embed_id}, session: {session_id}")

    return StreamingResponse(mock_stream_generator_aligned(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
    })
