import json
from typing import Dict, List, Any
from collections import defaultdict

# --- In-Memory Storage for Mock History ---
mock_chat_histories: Dict[str, List[Dict[str, str]]] = defaultdict(list)

# --- Helper to format response chunks ---
def format_sse_chunk(data: Dict[str, Any]) -> str:
    """Formats a dictionary into a Server-Sent Event string `data: {json}\n\n`."""
    return f"data: {json.dumps(data)}\n\n"
