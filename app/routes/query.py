import asyncio

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse

from app.utils.lightrag_init import query_rag, stream_query_rag, initialize_rag
from app.utils.auth import authenticate_request

router = APIRouter()

rag = asyncio.run(initialize_rag())

@router.get("/query")
async def query(
    query: str,
    _auth: bool = Depends(authenticate_request)   # <-- Universal authenticator dependency
):
    if rag is None:
        return JSONResponse(content={"error": "LightRAG system is not initialized."}, status_code=503)

    response = query_rag(rag, query)
    return JSONResponse(content={"response": response})

@router.get("/stream-query")
async def stream_query(
    request: Request, 
    query: str,
    _auth: bool = Depends(authenticate_request)   # <-- Universal authenticator dependency
):
    if rag is None:
        return JSONResponse(content={"error": "LightRAG system is not initialized."}, status_code=503)

    async def stream_generator():
        try:
            async for chunk in stream_query_rag(rag, query):
                yield chunk
        except Exception as e:
            yield f"[Streaming error: {str(e)}]"

    return StreamingResponse(stream_generator(), media_type="text/plain")
