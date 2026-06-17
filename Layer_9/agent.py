"""
DatasheetAI — Layer 9: Multi-Agent Orchestrator
══════════════════════════════════════════════
A state-graph routing agent that parses user queries, invokes calculations,
scores recommendations, generates PDF reports, and handles RAG search.
"""

import os
import sys
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Configure UTF-8 safe logger (avoids Windows cp1252 UnicodeEncodeError)
logger = logging.getLogger("datasheetai.agent")
if not logger.handlers:
    _handler = logging.StreamHandler(stream=open(os.devnull, "w"))  # suppress to devnull by default
    try:
        import io
        _handler = logging.StreamHandler(
            stream=io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        )
    except Exception:
        pass
    _handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# Ensure other project layers are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Layer_6.calculate import evaluate_cameras
from Layer_7.recommend import get_recommendations
from Layer_8.chat import chat_with_agent
from Layer_9.report_gen import generate_pdf_report

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ════════════════════════════════════════════
# SYSTEM PROMPTS
# ════════════════════════════════════════════

ROUTER_SYSTEM_PROMPT = """You are the master routing orchestrator of DatasheetAI, an industrial camera recommendation system.
Your job is to analyze the user's message and determine their execution intent.

Intents:
1. "recommendation": User is requesting camera selection, evaluating specifications against a physical layout, or providing parameters: conveyor speed (m/s), object size (mm), defect/crack size (mm), working distance (mm).
2. "rag_qa": User is asking specific technical questions about camera models, features, sensor names (e.g. Sony IMX264), interfaces, weight, operating temperatures, or general comparison between cameras.
3. "chat": General greetings, system help, or non-technical conversation.

Response format (valid JSON only):
{
  "intent": "recommendation" | "rag_qa" | "chat",
  "entities": {
    "conveyor_speed_ms": float or null,
    "object_size_mm": float or null,
    "defect_size_mm": float or null,
    "working_distance_mm": float or null,
    "search_query": string or null
  }
}
"""


# ════════════════════════════════════════════
# INTENT ROUTING
# ════════════════════════════════════════════

def route_query(query):
    """Call LLM in JSON mode to classify intent and extract parameters."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze: '{query}'"}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Routing error: {e}")
        return {"intent": "chat", "entities": {}}


# ════════════════════════════════════════════
# AGENT NODES
# ════════════════════════════════════════════

def execute_recommendation_flow(entities, state):
    """
    Evaluates requirements, runs calculation & scoring engines,
    compiles a summary, and creates the downloadable PDF report.
    """
    # Merge existing parameters from state if present (in case user updates parameters sequentially)
    last_req = state.get("last_requirements", {})
    
    conveyor_speed = entities.get("conveyor_speed_ms") or last_req.get("conveyor_speed_ms")
    object_size = entities.get("object_size_mm") or last_req.get("object_size_mm")
    defect_size = entities.get("defect_size_mm") or last_req.get("defect_size_mm")
    working_distance = entities.get("working_distance_mm") or last_req.get("working_distance_mm") or 500.0

    # If key parameters are missing, ask user for inputs
    missing = []
    if conveyor_speed is None: missing.append("Conveyor Speed (m/s)")
    if object_size is None: missing.append("Object Size (mm)")
    if defect_size is None: missing.append("Smallest Defect Size (mm)")

    if missing:
        msg = (
            "⚙️ I can run the industrial calculations and recommendation model for you! "
            f"Please specify the following details: **{', '.join(missing)}**."
        )
        return msg, state

    requirements = {
        "conveyor_speed_ms": float(conveyor_speed),
        "object_size_mm": float(object_size),
        "crack_size_mm": float(defect_size),
        "working_distance_mm": float(working_distance)
    }

    # Save to state
    state["last_requirements"] = requirements

    # Run Layer 6 (Calculation engine)
    calc_results = evaluate_cameras(requirements)
    
    # Run Layer 7 (Recommendation engine)
    rec_results = get_recommendations(requirements)

    state["last_analysis_results"] = {
        "calculated": calc_results["calculated"],
        "recommendations": rec_results
    }

    # Generate PDF Report
    pdf_filename = "camera_recommendation_report.pdf"
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), pdf_filename)
    
    try:
        generate_pdf_report(requirements, rec_results, pdf_path)
        state["pdf_report_path"] = pdf_path
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")

    # Format agent response
    calc = calc_results["calculated"]
    passing = [r for r in rec_results if r["passed"]]
    
    response = (
        f"### ⚙️ Engineering Analysis Completed\n\n"
        f"**Calculated Engineering Thresholds:**\n"
        f"- Minimum Frame Rate: **{calc['min_frame_rate_fps']} fps**\n"
        f"- Minimum Resolution: **{calc['min_resolution_pixels']} horizontal pixels**\n"
        f"- Maximum Exposure Limit: **{calc['max_exposure_time_ms']} ms**\n\n"
        f"**Recommendation Summary:**\n"
        f"Out of our database, **{len(passing)} cameras** meet the physical thresholds. "
    )
    
    if passing:
        best = passing[0]
        response += (
            f"The top-ranked model is **{best['product_name']}** ({best['manufacturer']}) "
            f"with a suitability score of **{best['score']}/100**.\n\n"
            f"You can download a full, detailed PDF analysis report in the sidebar or below!"
        )
    else:
        response += "\n\n❌ No cameras in the current database meet the requirements."

    return response, state


# ════════════════════════════════════════════
# MAIN AGENT SESSION RUNNER
# ════════════════════════════════════════════

def run_agent_session(user_input, state=None):
    """
    Master session coordinator called from the Streamlit frontend.
    Runs routing and dispatches execution to correct module/node.
    """
    if state is None:
        state = {
            "chat_history": [],
            "last_requirements": {},
            "last_analysis_results": {},
            "pdf_report_path": None
        }

    # Step 1: Route user intent
    routing = route_query(user_input)
    intent = routing.get("intent", "chat")
    entities = routing.get("entities", {})

    logger.info(f"Agent routing: {intent} (extracted: {entities})")

    # Step 2: Execute node
    if intent == "recommendation":
        response, updated_state = execute_recommendation_flow(entities, state)
    elif intent == "rag_qa":
        # Pass current query to Layer 8 RAG engine
        response = chat_with_agent(user_input, state.get("chat_history", []))
        updated_state = state
    else:
        # Standard chat fallback
        try:
            prompt = (
                "You are the senior assistant for DatasheetAI. Answer the user politely. "
                "Remind them you can run calculations, search cameras, or write PDF reports. "
                "Keep it concise."
            )
            chat_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.3
            )
            response = chat_response.choices[0].message.content
        except Exception as e:
            response = f"Hello! How can I help you choose industrial cameras today?"
        updated_state = state

    # Append interaction to chat history
    history = updated_state.setdefault("chat_history", [])
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})

    return {
        "response": response,
        "state": updated_state,
        "intent": intent,
        "pdf_report_path": updated_state.get("pdf_report_path")
    }


if __name__ == "__main__":
    # Ensure stdout handles encoding properly
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        
    print("═" * 55)
    print("  DatasheetAI — Multi-Agent Session Agent (CLI Test)")
    print("═" * 55)
    
    # Test session run
    test_state = {
        "chat_history": [],
        "last_requirements": {},
        "last_analysis_results": {},
        "pdf_report_path": None
    }
    
    # First: general query
    res = run_agent_session("I need to choose a camera for a conveyor at 3.0 m/s with 0.05mm cracks", test_state)
    print(f"\nAI Response:\n{res['response']}")
    print(f"\nReport created: {res['pdf_report_path']}")
