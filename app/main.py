import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from modular files
# from app.routes.stream_chat import router as stream_chat_router
from app.routes.history import router as history_router
from app.routes.widget import router as widget_router
from app.routes.ingestion import router as ingestion_router
from app.routes.query import router as query_router
from app.routes.workflow import router as workflow_router

# Import Supabase client
from app.utils.supabase import get_supabase_client

# Import LightRAG initialization
from app.utils.lightrag_init import initialize_rag, insert_data
from app.utils.scrape_website import scrape_site_from_sitemap

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

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
@app.on_event("startup")
async def initialize_lightrag():
    try:
        rag = asyncio.run(initialize_rag())
        app.state.rag = rag

        # insert_data(rag, "./mock.txt")
    except Exception as e:
        print(f"❌ Error initializing LightRAG: {str(e)}")

    
    # Insert data from the combined.txt file
    # scrape_site_from_sitemap("https://www.alphabase.co")
    # insert_data(rag, "./db/www.alphabase.co/combined.txt")

# Initialize Supabase tables if they don't exist
@app.on_event("startup")
async def initialize_supabase():
    try:
        supabase = await get_supabase_client()
        supabase.table("chat_histories").select("id").limit(1).execute()
        print("✅ Supabase connection successful")
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {str(e)}")


# app.include_router(stream_chat_router)
app.include_router(workflow_router)
app.include_router(history_router)
app.include_router(widget_router)
app.include_router(ingestion_router)
app.include_router(query_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)