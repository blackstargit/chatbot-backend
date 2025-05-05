import json
from typing import Dict, Any
import os
from urllib.parse import urlparse

from app.utils.scrape_website import scrape_site_from_sitemap
from app.utils.lightrag_init import insert_data

# --- Helper to format response chunks ---
def format_sse_chunk(data: Dict[str, Any]) -> str:
    """Formats a dictionary into a Server-Sent Event string `data: {json}\n\n`."""
    return f"data: {json.dumps(data)}\n\n"

async def process_frontend_url(app, frontend_url):
    """Process the frontend URL to scrape and insert data"""
    if not frontend_url:
        return
        
    # Parse the URL to get the base domain
    parsed_url = urlparse(frontend_url)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # Check if we've already processed this URL
    if app.state.frontend_url == base_domain:
        print(f"Already processed {base_domain}")
        return
        
    print(f"Processing new frontend URL: {base_domain}")
    app.state.frontend_url = base_domain
    
    # Check if the RAG system is initialized
    if not app.state.rag:
        print("RAG system not initialized, skipping scraping")
        return
        
    try:
        # Scrape the website
        print(f"Starting scraping of {base_domain}")
        folder = scrape_site_from_sitemap(base_domain)
        
        # Insert the data into RAG
        combined_file = f"{folder}/combined.txt"
        if os.path.exists(combined_file):
            print(f"Inserting data from {combined_file}")
            insert_data(app.state.rag, combined_file)
            print("Data insertion complete")
        else:
            print(f"Combined file not found: {combined_file}")
    except Exception as e:
        print(f"Error processing frontend URL: {str(e)}")