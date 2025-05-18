import asyncio
import json
import uuid
from fastapi import APIRouter, Path, Body, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse  # Changed back to StreamingResponse
from pydantic import ValidationError, BaseModel
import httpx
from typing import AsyncGenerator, Dict, Any

from app.utils.auth import authenticate_request
from app.types.types import StreamChatRequest
from app.utils.supabase import save_message

router = APIRouter()

# Replace with your actual n8n webhook URL
N8N_WEBHOOK_URL = "YOUR_N8N_INSTANCE_URL/webhook/d9716009-b1af-40c1-af88-f04d95123774"


@router.post("/embed/{embed_id}/chat")
async def chat_rag(
    request: Request,
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
    user_message_uuid = str(uuid.uuid4())
    user_message_entry = {"role": "user", "content": user_message_text, "uuid": user_message_uuid}
    assistant_message_uuid = str(uuid.uuid4())
    n8n_available = True

    # Handle Early Exits
    if not n8n_available:
        print("Error: n8n is unavailable")
        early_exit_data = {
            "uuid": str(uuid.uuid4()),
            "type": "textResponse",
            "textResponse": "I'm sorry, the chat service is currently unavailable. Please try again later.",
            "sources": [],
            "close": True,
            "error": True,
        }
        await save_message(session_id, user_message_entry)
        await save_message(session_id,  {"role": "assistant", "content": early_exit_data["textResponse"], "uuid": assistant_message_uuid})
        async def early_exit_generator():
            yield json.dumps(early_exit_data)
        return StreamingResponse(early_exit_generator, media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
        })

    try:
        async with httpx.AsyncClient() as client:
            n8n_response = await client.post(N8N_WEBHOOK_URL, json={"query_text": user_message_text})
            n8n_response.raise_for_status()
            n8n_data = n8n_response.json()
            print(f"Received response from n8n: {n8n_data}")

        if not isinstance(n8n_data, dict):
            raise ValueError("Expected a JSON object from n8n, but got a different type.")

        if "textResponse" not in n8n_data:
            raise ValueError("Expected 'textResponse' key in n8n response, but it was not found.")

        assistant_message_text = n8n_data["textResponse"]
        assistant_message_entry = {"role": "assistant", "content": assistant_message_text, "uuid": assistant_message_uuid}
        await save_message(session_id, user_message_entry)
        print(f"Saved user message for session {session_id} with UUID: {user_message_uuid}")
        await save_message(session_id, assistant_message_entry)
        print(f"Saved assistant response for session {session_id} with UUID: {assistant_message_uuid}")

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
            yield json.dumps(formatted_response)

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
