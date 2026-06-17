"""
DatasheetAI — Layer 8: Intelligent RAG Chat Assistant
═════════════════════════════════════════════════════
Retrieves camera context from the semantic vector store and leverages
gpt-4o-mini to answer technical industrial camera engineering questions.
"""

import os
import sys
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Configure UTF-8 safe logger
logger = logging.getLogger("datasheetai.chat")
if not logger.handlers:
    import io
    try:
        _h = logging.StreamHandler(
            stream=io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        )
    except Exception:
        _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

# Add project root to sys.path so we can import vector_store correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Layer_8.vector_store import semantic_search

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ════════════════════════════════════════════
# CORE RAG CHAT FUNCTION
# ════════════════════════════════════════════

def chat_with_agent(query, chat_history=None):
    """
    Generates a RAG response to the user's query by injecting
    semantic search results into the model context.
    
    Args:
        query: str, user's search query or question
        chat_history: list of dict, e.g. [{"role": "user", "content": "..."}, ...]
    """
    if chat_history is None:
        chat_history = []

    # Get top 3 relevant cameras from the vector store
    hits = []
    try:
        hits = semantic_search(query, top_k=3)
    except Exception as e:
        logger.warning(f"Vector store query failed: {e}")

    # Build context from semantic search results
    context_str = ""
    if hits:
        context_str = "Here are the most relevant camera models found in our database:\n\n"
        for i, hit in enumerate(hits, 1):
            context_str += f"--- MATCH #{i} (Confidence: {hit['similarity']:.1%}) ---\n"
            context_str += hit["profile"] + "\n\n"
    else:
        context_str = "No matching cameras found in the database.\n"

    system_prompt = f"""You are a senior industrial machine vision engineer and AI assistant for the DatasheetAI platform.
Your task is to answer user queries with precise, structured, and technical information about cameras.

Use the following DATABASE CONTEXT retrieved from our vector index to formulate your answer:
{context_str}

ENGINEERING INSTRUCTIONS:
1. Speak in a clear, professional, engineering-focused tone.
2. If comparing cameras, present comparison points (e.g. resolution, sensor size, frame rate, interfaces) in a structured or table format.
3. Be strict with specs and units (fps, pixels, um, g, °C, W).
4. If the database context has no answer, answer using general engineering knowledge but make it clear that the camera is not in our database.
5. If the user asks about calculations (e.g. conveyor speed, defect sizes), explain the physics principles, list the formulas, and note that they can perform evaluations in the 'Engineering Calculator' workspace.
"""

    messages = [{"role": "system", "content": system_prompt}]

    # Append recent chat history (keep last 6 turns to manage token limit)
    for interaction in chat_history[-6:]:
        messages.append({
            "role": interaction.get("role", "user"),
            "content": interaction.get("content", "")
        })

    # Append user prompt
    messages.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error communicating with AI: {e}"


# ============================================
# STANDALONE CLI CHAT LOOP
# ============================================

def _safe_print(msg=""):
    """Print that never crashes on Windows cp1252."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode())


def run_chat_cli():
    """Run RAG chat assistant in CLI mode."""
    _safe_print("=" * 55)
    _safe_print("  DatasheetAI -- Intelligent RAG Assistant")
    _safe_print("  Type 'quit' or 'exit' to exit.")
    _safe_print("=" * 55)

    history = []
    
    while True:
        try:
            print()
            user_input = input("You: ").strip()
            
            if user_input.lower() in ["quit", "exit"]:
                _safe_print("Goodbye!")
                break
                
            if not user_input:
                continue

            response = chat_with_agent(user_input, history)
            
            # Print response
            _safe_print(f"\nAI: {response}")
            
            # Append history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
            
        except KeyboardInterrupt:
            _safe_print("\nGoodbye!")
            break
        except Exception as e:
            _safe_print(f"\nError: {e}")


if __name__ == "__main__":
    run_chat_cli()