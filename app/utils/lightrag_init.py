from lightrag import LightRAG, QueryParam
from lightrag.llm.llama_index_impl import llama_index_complete_if_cache, llama_index_embed
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status

import asyncio
import os
import logging
import nest_asyncio

nest_asyncio.apply()

# Set up logger
logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

system_prompt_text = """
    You are a highly intelligent, exceptionally friendly, and engaging sales lead capture assistant. 
    Your core mission is to provide outstanding value to users through helpful and concise interactions.

    Your approach to lead capture (name and email) should be subtle and opportune. 
    Actively listen for cues of deeper interest from the user. 
    **Only when a user expresses clear interest in learning more (e.g., about specific features, pricing, benefits, next steps, or requests information that would be best sent to them), should you naturally and courteously offer to collect their details.** Frame this offer as a way to provide them with more personalized information, send requested materials, or facilitate a follow-up if they desire.

    **Key Guidelines:**

    * **Warm Engagement:** Always **respond** to greetings with genuine warmth and professionalism. Make the user feel welcome.
    * **Concise Value:** Provide clear, accurate, and succinct answers. If a user explicitly asks for more detail ("Can you explain more?", "Tell me more about X"), then you can provide a more thorough explanation.
    * **Informed Responses:** When questioned about the company, product, or service, offer informative and precise details.
    * **Respectful Interaction:** Always ensure the user feels heard, understood, and respected throughout the conversation.
    * **Contextual Lead Capture - Crucial:**
        * **Appropriate Times:** Look for moments where the user asks for something you could email (a brochure, a link, a summary), expresses a desire to explore further (e.g., "How can I try this?", "What are the next steps?"), or asks questions indicating significant buying interest.
        * **Inappropriate Times:** **Do NOT** attempt to capture lead information during greetings, simple pleasantries (e.g., user asks "how are you?"), general informational questions where no further follow-up is implied by the user, or if the user seems hesitant or is just casually Browse. The transition must feel helpful and non-intrusive to the user.

    Your goal is to be a helpful guide first, and a subtle lead capturer second, only when it genuinely enhances the user's journey.
"""

# Initialize with Google Gemini using the unified SDK
async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
    try:
        # Initialize GoogleGenerativeAI if not in kwargs
        if 'llm_instance' not in kwargs:
            llm_instance = GoogleGenAI(
                model="gemini-1.5-flash",  # or "gemini-2.0-flash" if available
                api_key=GEMINI_API_KEY,
                temperature=0.7,
            )
            kwargs['llm_instance'] = llm_instance

        # Handle the completion synchronously to avoid the await issue
        response = await llama_index_complete_if_cache(
            kwargs['llm_instance'],
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )
        return response
    except Exception as e:
        logger.error(f"LLM request failed: {str(e)}")
        raise

async def initialize_rag():
    # Ensure the working directory exists
    import os
    working_dir = os.environ.get("RAG_WORKING_DIR", "./rag_data")
    os.makedirs(working_dir, exist_ok=True)
    
    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            # Google embeddings dimension
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: llama_index_embed(
                texts,
                embed_model=GoogleGenAIEmbedding(
                    model_name="text-embedding-004",
                    api_key=GEMINI_API_KEY
                )
            ),
        ),
    )

    # Initialize storages
    await rag.initialize_storages()
    await initialize_pipeline_status()

    # rag.chunk_entity_relation_graph.embedding_func = rag.embedding_func

    return rag

# Function to process files with proper error handling
def insert_data(rag, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            print(f"Processing file")
            content = f.read()
            
            # Check if content is empty
            if not content or content.strip() == "":
                print("Error: Document content is empty")
                return False
                
            # Print content length for debugging
            print(f"Document content length: {len(content)} characters")
            
            # Add a try-except block specifically for the insert operation
            try:
                rag.insert(content)
                print(f"Successfully processed")
                return True
            except ValueError as ve:
                print(f"ValueError during RAG insert: {str(ve)}")
                # This is likely the 'Set of Tasks/Futures is empty' error
                if "Set of Tasks/Futures is empty" in str(ve):
                    print("This error typically occurs when the entity extraction process can't find any content to process.")
                    print("Check that your document has meaningful text that can be processed.")
                return False
            except Exception as insert_error:
                print(f"Error during RAG insert: {str(insert_error)}")
                return False
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return False

# Function to query the RAG system
def query_rag(rag, query_text):
    try:
        query = f"Please answer the following query according to the given system prompt: {query_text}"
        return rag.query(
            query, 
            system_prompt=system_prompt_text,
            param=QueryParam(stream=True)
            )
    except Exception as e:
        print(f"Error querying RAG: {str(e)}")
        return f"Error processing your query: {str(e)}"

# Function to stream query results from the RAG system
async def stream_query_rag(rag, query_text):
    """
    Stream query results from the RAG system
    
    Args:
        rag: The LightRAG instance
        query_text: The query text
        
    Yields:
        Chunks of the response as they are generated
    """

    query = f"Please answer the following query according to the given system prompt: {query_text}"

    try:
        print("Using QueryParam(stream=True) for streaming")
        # Use the query method with stream=True parameter
        result = rag.query(
            query,
            param=QueryParam(stream=True),
            system_prompt=system_prompt_text
        )
        
        # If it's not an async generator, it might be a synchronous iterable
        # or just a regular result
        if hasattr(result, '__iter__'):
            print("Contains __iter__")
            for chunk in result:
                yield chunk
                await asyncio.sleep(0.005)  # Small delay between chunks
        else:
            # If it's a regular result, simulate streaming by words
            print("Fallback to simulated streaming by words")
            result_str = str(result)
            words = result_str.split()
            
            for word in words:
                yield word + " "
                await asyncio.sleep(0.005)  # Simulate streaming with small delay
    except Exception as e:
        print(f"Error streaming query from RAG: {str(e)}")
        yield f"Error processing your query: {str(e)}"
