import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from modular files
from app.routes.stream_chat import router as stream_chat_router
from app.routes.history import router as history_router
from app.routes.widget import router as widget_router
from app.routes.ingestion import router as ingestion_router
from app.routes.query import router as query_router

# Import LightRAG initialization
from app.utils.lightrag_init import initialize_rag

# --- FastAPI Application Setup ---
app = FastAPI(
    title="RAG-Powered Embed API",
    description="API using LightRAG for responses, with Supabase for history storage and SSE streaming.",
    version="0.6.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize application state
app.state.frontend_url = None
app.state.rag = None

# Initialize LightRAG
try:
    rag = asyncio.run(initialize_rag())
    app.state.rag = rag

    print("✅ LightRAG initialized successfully")
except Exception as e:
    print(f"❌ Error initializing LightRAG: {str(e)}")


app.include_router(stream_chat_router)
app.include_router(history_router)
app.include_router(widget_router)
app.include_router(ingestion_router)
app.include_router(query_router)