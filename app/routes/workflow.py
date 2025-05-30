import asyncio
import json
import uuid
from fastapi import APIRouter, Path, Body, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse  # Changed back to StreamingResponse
from pydantic import ValidationError, BaseModel
import httpx
from typing import AsyncGenerator, Dict, Any
from app.utils.utils import format_sse_chunk
import os

from app.utils.auth import authenticate_request
from app.types.types import StreamChatRequest
from app.utils.supabase import save_message, ensure_user_chat_record, get_supabase_client

router = APIRouter()

# Replace with your actual n8n webhook URL
n8n_address = os.getenv('N8N_ADDRESS')
N8N_WEBHOOK_URL =   f"{n8n_address}/webhook/alphabot/chat"

@router.post("/embed/{embed_id}/stream-chat")
async def chat_rag(
    embed_id: str = Path(..., title="The ID of the embed configuration"),
    raw_body: str = Body(...),
    # _auth: bool = Depends(authenticate_request),
):
    """
    Handles chat requests, sending the query to n8n for processing
    and returns the response in the same format as a streaming response, but without actual streaming.
    """
    request_uuid = str(uuid.uuid4()) + "1fd"
    print(f"Request ID: {request_uuid}")
    print(f"Received chat request for embed_id: {embed_id}")
    print(f"Raw request body received: {raw_body}")

    try:
        data_dict = json.loads(raw_body)
        request_data = StreamChatRequest.model_validate(data_dict)
        print(f"Successfully parsed and validated request body from string.")
        print(f"Validated data: {request_data.model_dump(exclude_unset=True)}")
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON from raw body string.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON string in request body.",
        )
    except ValidationError as e:
        print(f"Error: Validation failed after parsing JSON string: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    session_id = request_data.session_id
    user_message_text = request_data.message
    client_user_id = request_data.client_user_id
    user_message_uuid = str(uuid.uuid4())
    user_message_entry = {"role": "user", "content": user_message_text, "uuid": user_message_uuid}
    assistant_message_uuid = str(uuid.uuid4())
    # n8n_available = True
    saved_user_message_data = None

    # # Handle Early Exits
    # if not n8n_available:
    #     print("Error: n8n is unavailable")
    #     early_exit_data = {
    #         "uuid": str(uuid.uuid4()),
    #         "type": "textResponse",
    #         "textResponse": "I'm sorry, the chat service is currently unavailable. Please try again later.",
    #         "sources": [],
    #         "close": True,
    #         "error": True,
    #     }
    #     await save_message(session_id, user_message_entry)
    #     await save_message(session_id,  {"role": "assistant", "content": early_exit_data["textResponse"], "uuid": assistant_message_uuid})
    #     async def early_exit_generator():
    #         yield json.dumps(early_exit_data)
    #     return StreamingResponse(early_exit_generator, media_type="text/event-stream", headers={
    #         "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
    #     })

    try:
        async with httpx.AsyncClient() as client:
            n8n_response = await client.post(N8N_WEBHOOK_URL, json={"query_text": user_message_text, "session_id": session_id})
            n8n_response.raise_for_status()
            n8n_data = n8n_response.json()
            print(f"Received response from n8n: {n8n_data}")

        if not isinstance(n8n_data, dict):
            raise ValueError("Expected a JSON object from n8n, but got a different type.")

        if "output" not in n8n_data:
            raise ValueError("Expected 'output' key in n8n response, but it was not found.")

        assistant_message_text = n8n_data["output"]
        assistant_message_entry = {"role": "assistant", "content": assistant_message_text, "uuid": assistant_message_uuid}
        saved_user_message_data = await save_message(session_id, user_message_entry)
        print(f"Saved user message for session {session_id} with UUID: {user_message_uuid}")
        
        user_message_timestamp = saved_user_message_data.get("created_at") # Get the actual timestamp
        
        supabase_client = await get_supabase_client() # Get Supabase client for the next operation
        await ensure_user_chat_record(
            supabase_client=supabase_client,
            client_user_id=client_user_id,
            embed_id=embed_id,
            session_id=session_id,
            first_message_content=user_message_text,
            message_timestamp=user_message_timestamp
        )


        await save_message(session_id, assistant_message_entry)
        print(f"Saved assistant response for session {session_id} with UUID: {assistant_message_uuid}")

        text_chunk_data = {
            "uuid": assistant_message_uuid,
            "type": "textResponseChunk",
            "textResponse": assistant_message_text,
            "sources": [],
            "close": False,
            "error": False,
        }

        # Construct the response in the same format as the final streaming chunk ("complete")
        formatted_response = {
            "uuid": assistant_message_uuid,
            "type": "complete",
            "textResponse": assistant_message_text,
            "sources": n8n_data.get("sources", []),  # Include sources if available from n8n
            "close": True,
            "error": False,
        }

        async def response_generator():
            yield format_sse_chunk(text_chunk_data)
            yield format_sse_chunk(formatted_response)

        return StreamingResponse(response_generator(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
        })

    except httpx.HTTPError as e:
        print(f"Error communicating with n8n: {e}")
        error_data = {
            "error": True,
            "message": f"Error communicating with n8n: {e}",
            "uuid": str(uuid.uuid4())
        }
        await save_message(session_id, user_message_entry)
        await save_message(session_id,  {"role": "assistant", "content": error_data["message"], "uuid": assistant_message_uuid})

        async def error_generator():
            yield json.dumps(error_data)
        return StreamingResponse(error_generator(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
        })
        #raise HTTPException(status_code=500, detail=error_data) # Removed HTTPException
    except ValueError as e:
        print(f"Error processing n8n response: {e}")
        error_data = {
            "error": True,
            "message": f"Error processing n8n response: {e}",
            "uuid": str(uuid.uuid4())
        }
        await save_message(session_id, user_message_entry)
        await save_message(session_id,  {"role": "assistant", "content": error_data["message"], "uuid": assistant_message_uuid})
        async def error_generator():
            yield json.dumps(error_data)
        return StreamingResponse(error_generator(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
        })
        #raise HTTPException(status_code=500, detail=error_data) # Removed HTTPException
