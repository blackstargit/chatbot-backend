import asyncio
import json
import uuid
from fastapi import APIRouter, Path, Body, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

# from app.utils.auth import authenticate_request

from app.types.types import StreamChatRequest
from app.utils.utils import format_sse_chunk
from app.utils.supabase import save_message
from app.utils.lightrag_init import query_rag, stream_query_rag

router = APIRouter()

@router.post("/embed/{embed_id}/stream-chat")
async def stream_chat_rag(
    request: Request,
    embed_id: str = Path(..., title="The ID of the embed configuration"),
    raw_body: str = Body(...),
    # _auth: bool = Depends(authenticate_request)   # <-- Injected AUTH here
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

    assistant_message_uuid = str(uuid.uuid4())

    # --- Check if RAG is initialized ---
    rag = request.app.state.rag
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
    
    # If we have early exit data, return it as a non-streaming response
    if early_exit_data:
        assistant_message_uuid = early_exit_data["uuid"]
        assistant_message_text = early_exit_data.get("textResponse", "")
        
        # If there's a valid text response, save it to history
        if assistant_message_text:
            assistant_message_entry = {"role": "assistant", "content": assistant_message_text, "uuid": assistant_message_uuid}
            
            # Save user message to Supabase
            await save_message(session_id, user_message_entry)
            print(f"Saved user message for session {session_id} with UUID: {user_message_uuid}")

            # Save assistant message to Supabase
            await save_message(session_id, assistant_message_entry)
            print(f"Saved assistant response for session {session_id} (early exit) with UUID: {assistant_message_uuid}")
        
        # Return a single SSE chunk with the early exit data
        async def early_exit_generator():
            yield format_sse_chunk(early_exit_data)
        
        return StreamingResponse(early_exit_generator(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
        })
    

    async def rag_stream_generator():
        start_data = {"uuid": assistant_message_uuid, "type": "start", "error": False, "sources": [], "textResponse": None, "close": False}
        yield format_sse_chunk(start_data)
        await asyncio.sleep(0.2)

        accumulated_text = ""
        try:
            async for chunk in stream_query_rag(rag, user_message_text):
                if isinstance(chunk, str):
                    chunk_text = chunk
                else:
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
        
        # Save user message to Supabase
        await save_message(session_id, user_message_entry)
        print(f"Saved user message for session {session_id} with UUID: {user_message_uuid}")

        assistant_message_entry = {"role": "assistant", "content": accumulated_text, "uuid": assistant_message_uuid}
        await save_message(session_id, assistant_message_entry)
        print(f"Saved assistant response for session {session_id} (streaming) with UUID: {assistant_message_uuid}")


    return StreamingResponse(rag_stream_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
    })
