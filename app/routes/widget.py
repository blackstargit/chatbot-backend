from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get(
    "/widget-snippet",
    response_class=HTMLResponse,      # documents as text/html :contentReference[oaicite:0]{index=0}
)
def widget_snippet():
    js = """
    <script 
      data-open-on-load="on"
      src="/dist/anythingllm-chat-widget.js"
      data-base-api-url='http://localhost:8000/embed' 
      data-embed-id="example-uuid" 
      data-sponsor-link="https://alphabase.co/" 
      data-sponsor-text="Powered by Alphabase"
      data-chat-icon="chatBubble"
      data-brand-image-url="https://framerusercontent.com/images/OJTBlYkWEYh1WN4Ylt1HSog.png"
      data-greeting="Hello! How can I help you today?"
      data-assistant-name="AlphaBot"
      data-assistant-icon="https://i.ibb.co/5WJfXJ0x/bg-white-bot.png"
      data-window-width="500px"
      data-default-messages="Tell me about Alphabase, What's new?, What are your features?"
      data-show-thoughts="true"
    ></script>
    """
    # HTMLResponse will set Content-Type: text/html by default :contentReference[oaicite:1]{index=1}
    return HTMLResponse(content=js)