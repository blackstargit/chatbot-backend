import json
from typing import Dict, Any

# --- Helper to format response chunks ---
def format_sse_chunk(data: Dict[str, Any]) -> str:
    """Formats a dictionary into a Server-Sent Event string `data: {json}\n\n`."""
    return f"data: {json.dumps(data)}\n\n"
