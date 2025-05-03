import asyncio
import json
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Path, Body, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.types.types import StreamChatRequest
from app.utils.utils import format_sse_chunk
from app.utils.supabase import save_message
from app.rag.lightrag_init import query_rag, stream_query_rag

router = APIRouter()

@router.post("/embed/{embed_id}/stream-chat")
async def stream_chat_rag(
    request: Request,
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
    
    # Save user message to Supabase
    await save_message(session_id, user_message_entry)
    print(f"Saved user message for session {session_id} with UUID: {user_message_uuid}")

    # --- Check if RAG is initialized ---
    rag = request.app.state.rag
    assistant_response_text = None
    early_exit_data = None # Store data for early exit chunks
    sources = []
    
    # Handle Early Exits
    if rag is None:
        print("Error: LightRAG not initialized")
        early_exit_data = {
            "uuid": str(uuid.uuid4()),
            "type": "textResponse",
            "textResponse": "I'm sorry, the RAG system is currently unavailable. Please try again later.",
            "sources": [],
            "close": True,
            "error": True
        }
    elif "help" in user_message_text.lower():
        print("Processing help request")
        early_exit_data = {
            "uuid": str(uuid.uuid4()),
            "type": "textResponse",
            "textResponse": "I'm here to help answer questions about your documents. What would you like to know?",
            "sources": [],
            "close": True,
            "error": False
        }
    
    # If we have early exit data, return it as a non-streaming response
    if early_exit_data:
        assistant_message_uuid = early_exit_data["uuid"]
        assistant_message_text = early_exit_data.get("textResponse", "")
        
        # If there's a valid text response, save it to history
        if assistant_message_text:
            assistant_message_entry = {"role": "assistant", "content": assistant_message_text, "uuid": assistant_message_uuid}
            
            # Save assistant message to Supabase
            await save_message(session_id, assistant_message_entry)
            print(f"Saved assistant response for session {session_id} (early exit) with UUID: {assistant_message_uuid}")
        
        # Return a single SSE chunk with the early exit data
        async def early_exit_generator():
            yield format_sse_chunk(early_exit_data)
        
        return StreamingResponse(early_exit_generator(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
        })
    
    # --- Main Chat Flow ---
    # If no early exit, prepare for streaming from the RAG system 
    # TODO: WTF does this mean ^
    if not early_exit_data:
        try:
            print(f"Querying LightRAG with: {user_message_text}")
            
            # For non-streaming response, we still need to get sources and save a complete message
            # Get a non-streaming response to extract sources and save to history
            rag_response = query_rag(rag, user_message_text)
            
            # Extract sources if available
            if hasattr(rag_response, 'sources') and rag_response.sources:
                for source in rag_response.sources:
                    sources.append({
                        "text": source.text[:200] + "...",  # Truncate long source texts
                        "title": source.metadata.get("title", "Document"),
                        "url": source.metadata.get("url", None)
                    })
            
            # Set the complete response text for history saving
            if isinstance(rag_response, str):
                assistant_response_text = rag_response
            else:
                assistant_response_text = str(rag_response)
                
            print(f"Got complete response from LightRAG for history: {assistant_response_text[:100]}...")
            
        except Exception as e:
            print(f"Error querying RAG: {str(e)}")
            assistant_response_text = f"I encountered an error while processing your query. Please try again or rephrase your question. Error: {str(e)}"
    
    # Create a UUID for the assistant message
    assistant_message_uuid = str(uuid.uuid4())
    
    # Save the assistant message to history
    assistant_message_entry = {"role": "assistant", "content": assistant_response_text, "uuid": assistant_message_uuid}
    
    # Save assistant message to Supabase
    await save_message(session_id, assistant_message_entry)
    print(f"Saved assistant response for session {session_id} (streaming) with UUID: {assistant_message_uuid}")

    # Define the generator for streaming
    async def rag_stream_generator():
        # 1. Start chunk - use the same UUID as the assistant message for consistency
        start_data = {"uuid": assistant_message_uuid, "type": "start", "error": False, "sources": [], "textResponse": None, "close": False}
        yield format_sse_chunk(start_data)
        await asyncio.sleep(0.2)

        # 2. Stream text chunks directly from LightRAG
        accumulated_text = ""
        try:
            async for chunk in stream_query_rag(rag, user_message_text):
                # Handle different types of chunks
                if isinstance(chunk, str):
                    chunk_text = chunk
                else:
                    # If it's an object with a specific structure, extract the text
                    chunk_text = str(chunk)
                
                accumulated_text += chunk_text
                
                text_chunk_data = {
                    "uuid": assistant_message_uuid,
                    "type": "textResponseChunk",
                    "textResponse": chunk_text,
                    "sources": [],
                    "close": False,
                    "error": False,
                }
                yield format_sse_chunk(text_chunk_data)
        except Exception as e:
            print(f"Error during streaming: {str(e)}")
            error_chunk = {
                "uuid": assistant_message_uuid,
                "type": "textResponseChunk",
                "textResponse": f" [Error during streaming: {str(e)}]",
                "sources": [],
                "close": False,
                "error": True,
            }
            yield format_sse_chunk(error_chunk)
            
            # If we had an error during streaming but already got a complete response earlier,
            # use that instead of the accumulated text which might be incomplete
            if not accumulated_text and assistant_response_text:
                accumulated_text = assistant_response_text

        # 3. Complete chunk
        complete_data = {
            "uuid": assistant_message_uuid,
            "type": "complete",
            "textResponse": None,
            "sources": sources,
            "close": True,
            "error": False,
        }
        yield format_sse_chunk(complete_data)
        print(f"Finished streaming RAG response for embed_id: {embed_id}, session: {session_id}")
        
        # If the accumulated text differs from what we saved to history,
        # update the history with the actual streamed text
        if accumulated_text and accumulated_text != assistant_response_text:
            print("Updating history with actual streamed text")
            updated_message = {"role": "assistant", "content": accumulated_text, "uuid": assistant_message_uuid}
            await save_message(session_id, updated_message, update=True)

    return StreamingResponse(rag_stream_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
    })
