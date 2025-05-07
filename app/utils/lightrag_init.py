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
        # For production, consider using PostgreSQL-based storage
        # kv_storage="PGKVStorage",
        # doc_status_storage="PGDocStatusStorage",
        # graph_storage="PGGraphStorage",
        # vector_storage="PGVectorStorage",
        # auto_manage_storages_states=False,
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
        system_prompt_text = """
            You are a highly intelligent and polite sales lead capture assistant. Your primary goal is to engage users in a helpful and informative way, while gradually and naturally collecting their contact information (such as name, email, and phone number).
            - Always respond to greetings with a warm and professional greeting.
            - Provide clear, accurate, and concise answers to user questions based on the context.
            - Whenever a user asks about the company, product, or service, provide detailed but precise information, and follow up by asking if they would like to be contacted.
            - Transition every interaction—regardless of the topic—toward collecting lead information in a friendly, non-intrusive manner.
            - Ask for their contact details using natural, engaging language (e.g., "Would it be alright if I get your name and email so someone from our team can reach out to assist you further?").
            Always ensure the user feels heard, respected, and that sharing their contact info will result in helpful follow-up.
        """
        query = f"Please answer the following query according to the given system prompt: {query_text}"
        return rag.query(
            query, 
            system_prompt=system_prompt_text, 
            param=QueryParam(stream=True, mode="bypass")
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
    try:
        system_prompt_text = """
            You are a highly intelligent and polite sales lead capture assistant. Your primary goal is to engage users in a helpful and informative way, while gradually and naturally collecting their contact information (such as name, email, and phone number).
            - Always respond to greetings with a warm and professional greeting.
            - Provide clear, accurate, and concise answers to user questions based on the context.
            - Whenever a user asks about the company, product, or service, provide detailed but precise information, and follow up by asking if they would like to be contacted.
            - Transition every interaction—regardless of the topic—toward collecting lead information in a friendly, non-intrusive manner.
            - Ask for their contact details using natural, engaging language (e.g., "Would it be alright if I get your name and email so someone from our team can reach out to assist you further?").
            Always ensure the user feels heard, respected, and that sharing their contact info will result in helpful follow-up.
        """
        
        print("Using QueryParam(stream=True) for streaming")
        # Use the query method with stream=True parameter
        result = rag.query(
            query_text,
            param=QueryParam(stream=True, mode="bypass"),
            system_prompt=system_prompt_text
        )
        
        # If it's not an async generator, it might be a synchronous iterable
        # or just a regular result
        if hasattr(result, '__iter__'):
            print("Contains __iter__")
            for chunk in result:
                yield chunk
                await asyncio.sleep(0.001)  # Small delay between chunks
        else:
            # If it's a regular result, simulate streaming by words
            print("Fallback to simulated streaming by words")
            result_str = str(result)
            words = result_str.split()
            
            for word in words:
                yield word + " "
                await asyncio.sleep(0.001)  # Simulate streaming with small delay
    except Exception as e:
        print(f"Error streaming query from RAG: {str(e)}")
        yield f"Error processing your query: {str(e)}"
