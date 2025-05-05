from fastapi import APIRouter, Request

from app.utils.lightrag_init import query_rag, stream_query_rag
from fastapi.responses import StreamingResponse, JSONResponse

router = APIRouter()

@router.get("/query")
async def query(request: Request, query: str):
    rag = request.app.state.rag
    query = query_rag(rag, query)
    return JSONResponse(content={"response": query})

@router.get("/stream-query")
async def stream_query(request: Request, query: str):
    rag = request.app.state.rag
    query = stream_query_rag(rag, query)
    return StreamingResponse(content=query)
