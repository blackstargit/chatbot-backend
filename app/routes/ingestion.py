import os
import asyncio
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Form, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import HttpUrl

from app.utils.scrape_website import scrape_site_from_sitemap
from app.utils.lightrag_init import insert_data
from app.utils.doc_support import extract_pdf_text, extract_docx_text, extract_txt_text, get_file_type

router = APIRouter()

# ---------- 🚀 FastAPI Endpoint ----------

@router.post("/ingest/file")
async def ingest(request: Request, file: UploadFile = File(...)):
    file_bytes = await file.read()
    file_type = get_file_type(file.filename, file.content_type)

    if file_type == 'unsupported':
        raise HTTPException(status_code=400, detail="Unsupported file type. Only PDF, DOCX, TXT allowed.")

    # Route to appropriate extractor
    if file_type == 'pdf':
        extracted_text = extract_pdf_text(file_bytes)
    elif file_type == 'docx':
        extracted_text = extract_docx_text(file_bytes)
    elif file_type == 'txt':
        extracted_text = extract_txt_text(file_bytes)

    os.makedirs("db/documents", exist_ok=True)
    with open(f"db/documents/{file.filename}", "w", encoding="utf-8") as f:
        f.write(extracted_text)

    # Check if extracted text is empty
    if not extracted_text or extracted_text.strip() == "":
        raise HTTPException(status_code=400, detail="Extracted text is empty. Cannot process document.")

    # TODO: add a index or check to avoid double adding a document
    insert_data(request.app.state.rag, f"db/documents/{file.filename}")

    query = request.app.state.rag.query("List my resume?")
    return JSONResponse(content={
        "type": "document",
        "file_name": file.filename,
        "file_type": file_type,
        "query": query
    })


@router.post("/ingest/url")
async def ingest(request: Request, url: str):
    url = unquote(url)
    folder = scrape_site_from_sitemap(url)

    if os.path.exists(f"{folder}/combined.txt"):
        insert_data(request.app.state.rag, f"{folder}/combined.txt")
        
        query = request.app.state.rag.query("List my resume?")
        return JSONResponse(content={
            "type": "website",
            "url": url,
            "query": query
        })




