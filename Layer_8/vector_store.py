"""
DatasheetAI — Layer 8: Semantic Vector Store
══════════════════════════════════════════
Builds a semantic index of camera profiles and provides cosine similarity search.
Uses OpenAI text-embedding-3-small.
"""

import os
import json
import logging
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

# Configure UTF-8 safe logger
logger = logging.getLogger("datasheetai.vector_store")
if not logger.handlers:
    import io, sys as _sys
    try:
        _h = logging.StreamHandler(
            stream=io.TextIOWrapper(_sys.stderr.buffer, encoding="utf-8", errors="replace")
        )
    except Exception:
        _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

# ════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "datasheetai",
}

EMBEDDING_MODEL = "text-embedding-3-small"
STORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_embeddings.json")


# ════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════

def generate_camera_profile(camera):
    """Generate a cohesive text profile representing all specs for embedding search."""
    name = camera.get("product_name", camera.get("Product Name", "Unknown"))
    mfg = camera.get("manufacturer", camera.get("Manufacturer", "Unknown"))
    res = camera.get("resolution", camera.get("Resolution", "N/A"))
    fps = camera.get("frame_rate", camera.get("Frame Rate", "N/A"))
    px_size = camera.get("pixel_size", camera.get("Pixel Size", "N/A"))
    sensor_size = camera.get("sensor_size", camera.get("Sensor Size", "N/A"))
    tech = camera.get("sensor_technology", camera.get("Sensor Technology", "N/A"))
    interface = camera.get("interface", camera.get("Interface", "N/A"))
    bit_depth = camera.get("bit_depth", camera.get("Bit Depth", "N/A"))
    weight = camera.get("weight", camera.get("Weight", "N/A"))
    temp = camera.get("operating_temperature", camera.get("Operating Temperature", "N/A"))
    power = camera.get("power_consumption", camera.get("Power Consumption", "N/A"))
    mount = camera.get("lens_mount", camera.get("Lens Mount", "N/A"))
    sensor_name = camera.get("sensor_name", camera.get("Sensor Name", "N/A"))

    profile = (
        f"Camera Model: {name} by {mfg}\n"
        f"Specifications:\n"
        f"- Resolution: {res}\n"
        f"- Frame Rate: {fps}\n"
        f"- Pixel Size: {px_size}\n"
        f"- Sensor Optical Size: {sensor_size}\n"
        f"- Sensor Technology & Shutter: {tech}\n"
        f"- Interface Connection: {interface}\n"
        f"- Bit Depth: {bit_depth}\n"
        f"- Physical Weight: {weight}\n"
        f"- Operating Temp Range: {temp}\n"
        f"- Electrical Power Consumption: {power}\n"
        f"- Lens Mount support: {mount}\n"
        f"- Internal Sensor Model: {sensor_name}"
    )
    return profile


def get_embedding(text):
    """Retrieve dense vector embedding from OpenAI."""
    try:
        cleaned = str(text).replace("\n", " ").strip()
        response = client.embeddings.create(input=[cleaned], model=EMBEDDING_MODEL)
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"OpenAI Embedding API error: {e}")
        return []


def get_embeddings_batch(texts):
    """Retrieve dense vector embeddings from OpenAI for a list of texts in a single batch API call."""
    try:
        cleaned_texts = [str(text).replace("\n", " ").strip() for text in texts]
        response = client.embeddings.create(input=cleaned_texts, model=EMBEDDING_MODEL)
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"OpenAI Embedding API batch error: {e}")
        return []


# ════════════════════════════════════════════
# CORE VECTOR STORE OPERATIONS
# ════════════════════════════════════════════

def build_vector_store(cameras=None):
    """
    Build vector embeddings for all cameras and save to JSON.
    If cameras is None, loads current records from MySQL.
    """
    if cameras is None:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM cameras")
            cameras = cursor.fetchall()
            for cam in cameras:
                for k, v in list(cam.items()):
                    if hasattr(v, "isoformat"):
                        cam[k] = v.isoformat()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            # Fallback to normalized JSON in Layer 3
            l3_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Layer_3", "normalized_cameras.json")
            if os.path.exists(l3_file):
                logger.warning("Falling back to Layer 3 JSON file...")
                with open(l3_file, "r", encoding="utf-8") as f:
                    cameras = json.load(f)
            else:
                cameras = []

    if not cameras:
        logger.warning("No cameras to index.")
        return False

    logger.info(f"Generating embeddings for {len(cameras)} cameras...")
    embeddings_list = []
    
    # Batch processing (e.g. 100 cameras at a time)
    batch_size = 100
    for idx in range(0, len(cameras), batch_size):
        batch = cameras[idx : idx + batch_size]
        profiles = [generate_camera_profile(cam) for cam in batch]
        
        logger.info(f"   [{min(idx + batch_size, len(cameras))}/{len(cameras)}] Fetching batch embeddings...")
        vectors = get_embeddings_batch(profiles)
        
        if len(vectors) == len(batch):
            for cam, profile, vector in zip(batch, profiles, vectors):
                embeddings_list.append({
                    "camera": cam,
                    "profile": profile,
                    "embedding": vector
                })
        else:
            logger.warning(f"Batch size mismatch (expected {len(batch)}, got {len(vectors)}). Processing individually...")
            for i, cam in enumerate(batch):
                name = cam.get("product_name", cam.get("Product Name", "Unknown"))
                profile = profiles[i]
                logger.info(f"   [{idx + i + 1}/{len(cameras)}] Embedding: {name} (individual fallback)...")
                vector = get_embedding(profile)
                if vector:
                    embeddings_list.append({
                        "camera": cam,
                        "profile": profile,
                        "embedding": vector
                    })

    # Save to local store file
    data_to_save = {
        "model": EMBEDDING_MODEL,
        "count": len(embeddings_list),
        "embeddings": embeddings_list
    }
    
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Vector store built and saved to: {os.path.basename(STORE_FILE)}")
    return True



def semantic_search(query, top_k=3):
    """
    Query the local vector store for semantically similar cameras.
    Returns list of dict: {"camera": camera_dict, "similarity": float}
    """
    if not os.path.exists(STORE_FILE):
        logger.warning("Vector store file not found. Building first...")
        build_vector_store()
        
    if not os.path.exists(STORE_FILE):
        return []

    with open(STORE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    query_vector = get_embedding(query)
    if not query_vector:
        return []

    results = []
    for entry in data.get("embeddings", []):
        db_vector = entry["embedding"]
        # Dot product (vectors are pre-normalized by OpenAI to length 1.0)
        similarity = sum(q * d for q, d in zip(query_vector, db_vector))
        
        results.append({
            "camera": entry["camera"],
            "profile": entry["profile"],
            "similarity": round(similarity, 4)
        })

    # Sort by similarity descending
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


# ============================================
# STANDALONE CLI TEST RUN
# ============================================

if __name__ == "__main__":
    def _safe_print(msg=""):
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode("ascii", errors="replace").decode())

    _safe_print("=" * 55)
    _safe_print("  DatasheetAI -- Semantic Vector Indexer")
    _safe_print("=" * 55)
    
    # Build
    build_vector_store()
    
    # Test query
    test_query = "USB 3.0 camera with high speed for industrial assembly line"
    _safe_print(f"\nSearching for: '{test_query}'")
    hits = semantic_search(test_query, top_k=2)
    
    for i, hit in enumerate(hits, 1):
        cam = hit["camera"]
        _safe_print(f"\n  Match #{i} (Similarity: {hit['similarity']:.1%})")
        _safe_print(f"  {cam.get('product_name', cam.get('Product Name'))} ({cam.get('manufacturer', cam.get('Manufacturer'))})")
        _safe_print(f"     FPS: {cam.get('frame_rate', cam.get('Frame Rate'))} | Res: {cam.get('resolution', cam.get('Resolution'))}")
