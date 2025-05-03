from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from modular files
from app.routes.stream_chat import router as stream_chat_router
from app.routes.history import router as history_router

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Mock Embed API (Manual Parse + History + Aligned SSE)",
    description="Mock API simulating responses, storing history, aligning SSE format. Handles stringified JSON body.",
    version="0.5.0" # Bump version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from modular files
app.include_router(stream_chat_router)
app.include_router(history_router)

