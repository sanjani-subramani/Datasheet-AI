"""
DatasheetAI — Layer 2: Intelligent Specification Extraction Engine
═══════════════════════════════════════════════════════════════════
Uses OpenAI GPT-4o-mini with Structured Outputs (Pydantic) to extract
camera specifications from any messy PDF text. Supports multi-camera
documents, confidence scoring, and automatic deduplication.
"""

import os
import re
import sys
import json
import time
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# ════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"
MAX_CHUNK_CHARS = 14000  # Safe limit per API call


# ════════════════════════════════════════════
# PYDANTIC SCHEMAS — Structured Output
# ════════════════════════════════════════════

class ConfidenceScores(BaseModel):
    """Per-field confidence scores from the AI extractor (0.0–1.0)."""
    product_name: float = Field(0.0, description="Confidence for product name extraction")
    manufacturer: float = Field(0.0, description="Confidence for manufacturer extraction")
    resolution: float = Field(0.0, description="Confidence for resolution extraction")
    frame_rate: float = Field(0.0, description="Confidence for frame rate extraction")
    pixel_size: float = Field(0.0, description="Confidence for pixel size extraction")
    sensor_size: float = Field(0.0, description="Confidence for sensor size extraction")
    sensor_technology: float = Field(0.0, description="Confidence for sensor technology extraction")
    interface: float = Field(0.0, description="Confidence for interface extraction")
    bit_depth: float = Field(0.0, description="Confidence for bit depth extraction")
    weight: float = Field(0.0, description="Confidence for weight extraction")
    operating_temperature: float = Field(0.0, description="Confidence for operating temp extraction")
    power_consumption: float = Field(0.0, description="Confidence for power consumption extraction")
    lens_mount: float = Field(0.0, description="Confidence for lens mount extraction")
    sensor_name: float = Field(0.0, description="Confidence for sensor name extraction")


class CameraSpec(BaseModel):
    """Single camera specification extracted from a datasheet."""
    product_name: Optional[str] = Field(None, description="Camera model name/number (e.g. acA2040-90um)")
    manufacturer: Optional[str] = Field(None, description="Camera manufacturer (e.g. Basler, FLIR, Sony)")
    resolution: Optional[str] = Field(None, description="Resolution as 'H x V pixels' (e.g. '2048 x 2048 pixels')")
    frame_rate: Optional[str] = Field(None, description="Max frame rate with unit (e.g. '90 fps')")
    pixel_size: Optional[str] = Field(None, description="Pixel size with unit (e.g. '5.5 x 5.5 um')")
    sensor_size: Optional[str] = Field(None, description="Sensor optical format (e.g. '1 inch', '2/3 inch')")
    sensor_technology: Optional[str] = Field(None, description="Sensor type (e.g. 'CMOS, global shutter')")
    interface: Optional[str] = Field(None, description="Communication interface (e.g. 'USB 3.0', 'GigE Vision')")
    bit_depth: Optional[str] = Field(None, description="Supported bit depths (e.g. '8 bit, 12 bit')")
    weight: Optional[str] = Field(None, description="Camera weight with unit (e.g. '65 g')")
    operating_temperature: Optional[str] = Field(None, description="Operating temp range (e.g. '0°C – 50°C')")
    power_consumption: Optional[str] = Field(None, description="Power consumption (e.g. '3.0 W')")
    lens_mount: Optional[str] = Field(None, description="Lens mount type (e.g. 'C', 'CS', 'C, CS')")
    sensor_name: Optional[str] = Field(None, description="Sensor model (e.g. 'Sony IMX264', 'CMOSIS CMV4000')")
    confidence: ConfidenceScores = Field(default_factory=ConfidenceScores)


class ExtractionResult(BaseModel):
    """All cameras extracted from a datasheet chunk."""
    cameras: List[CameraSpec] = Field(default_factory=list, description="All individual camera models found")


# ════════════════════════════════════════════
# FIELD MAPPING — snake_case → Title Case
# ════════════════════════════════════════════

SPEC_FIELDS = [
    "product_name", "manufacturer", "resolution", "frame_rate",
    "pixel_size", "sensor_size", "sensor_technology", "interface",
    "bit_depth", "weight", "operating_temperature", "power_consumption",
    "lens_mount", "sensor_name",
]

FIELD_MAP = {
    "product_name": "Product Name",
    "manufacturer": "Manufacturer",
    "resolution": "Resolution",
    "frame_rate": "Frame Rate",
    "pixel_size": "Pixel Size",
    "sensor_size": "Sensor Size",
    "sensor_technology": "Sensor Technology",
    "interface": "Interface",
    "bit_depth": "Bit Depth",
    "weight": "Weight",
    "operating_temperature": "Operating Temperature",
    "power_consumption": "Power Consumption",
    "lens_mount": "Lens Mount",
    "sensor_name": "Sensor Name",
}


# ════════════════════════════════════════════
# SMART CHUNKING BY PAGE BOUNDARIES
# ════════════════════════════════════════════

def chunk_by_pages(text, max_chars=MAX_CHUNK_CHARS):
    """Split document text into chunks by page boundaries."""
    # Split on page markers like "--- Page 1 ---"
    segments = re.split(r'(---\s*Page\s+\d+\s*---)', text)

    # Reassemble: pair each page header with its content
    pages = []
    current = ""
    for seg in segments:
        if re.match(r'---\s*Page\s+\d+\s*---', seg):
            if current.strip():
                pages.append(current.strip())
            current = seg + "\n"
        else:
            current += seg
    if current.strip():
        pages.append(current.strip())

    if not pages:
        # No page markers — fall back to char-based splitting
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    # Group pages into chunks under the character limit
    chunks = []
    current_chunk = ""
    for page in pages:
        if len(current_chunk) + len(page) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = page
        else:
            current_chunk = (current_chunk + "\n\n" + page).strip()
    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text]


# ════════════════════════════════════════════
# AI EXTRACTION — GPT-4o-mini Structured Output
# ════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert industrial camera specification extractor used by Google-level engineering teams.

EXTRACTION RULES:
1. Extract EVERY INDIVIDUAL camera model from the text. Each model gets its own entry.
2. Do NOT merge different camera models — even if they share some specifications.
3. Extract as many fields as possible for each camera.
4. For confidence scores: rate 0.0–1.0 how confident you are in each extraction:
   - 1.0 = explicitly stated, no ambiguity
   - 0.7–0.9 = strongly implied or clearly derivable
   - 0.4–0.6 = partially visible, some inference needed
   - 0.1–0.3 = highly uncertain, major inference
   - 0.0 = field not found at all (leave value as null)
5. Normalize units consistently:
   - Frame rate: use 'fps' (e.g., '90 fps')
   - Pixel size: use 'um' with 'x' separator (e.g., '5.5 x 5.5 um')
   - Weight: use 'g' (e.g., '65 g')
   - Resolution: use 'H x V pixels' (e.g., '2048 x 2048 pixels')
   - Power: use 'W' (e.g., '3.0 W')
   - Temperature: use '°C' (e.g., '0°C – 50°C')
6. If a shared specification row applies to multiple models, copy it to each model.
7. Camera model names often contain suffixes like gm/gc (mono/color) — extract both as separate entries if distinct specs exist, or as one entry with '/gc' suffix if specs are identical.
8. If the text is marketing material with no specific camera models, return empty cameras list."""


def extract_cameras_from_chunk(chunk_text, source_file, chunk_idx, total_chunks):
    """Extract cameras from a single text chunk via GPT-4o-mini structured output."""
    print(f"    🤖 Chunk {chunk_idx}/{total_chunks} ({len(chunk_text):,} chars) → GPT-4o-mini...")

    user_prompt = f"""Extract ALL camera model specifications from this datasheet text.

Source: {source_file}

---
{chunk_text}
---"""

    try:
        response = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=ExtractionResult,
            temperature=0,
        )
        result = response.choices[0].message.parsed
        cameras = result.cameras if result else []
        print(f"       → {len(cameras)} camera(s) extracted")
        return cameras

    except Exception as e:
        print(f"    ❌ API Error on chunk {chunk_idx}: {e}")
        # Fallback: try without structured output
        return _fallback_extraction(chunk_text, source_file)


def _fallback_extraction(text, source_file):
    """Fallback extraction using standard JSON mode if structured output fails."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\n\nReturn valid JSON only. Format: {\"cameras\": [...]}"},
                {"role": "user", "content": f"Extract camera specs from:\n{text[:8000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        cameras = []
        for cam_data in data.get("cameras", []):
            cameras.append(CameraSpec(**cam_data))
        return cameras
    except Exception as e:
        print(f"    ❌ Fallback also failed: {e}")
        return []


# ════════════════════════════════════════════
# POST-PROCESSING — Deduplication & Formatting
# ════════════════════════════════════════════

def camera_to_dict(cam: CameraSpec) -> dict:
    """Convert CameraSpec → output dict with Title Case keys."""
    output = {}
    for snake_key in SPEC_FIELDS:
        value = getattr(cam, snake_key, None)
        if value is not None and str(value).strip():
            title_key = FIELD_MAP[snake_key]
            output[title_key] = str(value).strip()

    # Build confidence dict with Title Case keys
    conf = cam.confidence
    conf_dict = {}
    for snake_key in SPEC_FIELDS:
        score = getattr(conf, snake_key, 0.0)
        conf_dict[FIELD_MAP[snake_key]] = round(score, 2)
    output["confidence_scores"] = conf_dict

    return output


def count_fields(cam_dict):
    """Count non-null spec fields (excluding metadata keys)."""
    skip = {"confidence_scores"}
    return sum(1 for k, v in cam_dict.items()
               if k not in skip and v is not None and str(v).strip())


def deduplicate_cameras(cameras):
    """Remove duplicates by product name, keeping the richest entry."""
    seen = {}
    for cam in cameras:
        name = cam.get("Product Name", "")
        if not name:
            continue
        # Normalize the name for comparison
        key = re.sub(r'\s+', ' ', name.strip().lower())
        if key not in seen or count_fields(cam) > count_fields(seen[key]):
            seen[key] = cam
    return list(seen.values())


def safe_filename(name):
    """Create filesystem-safe filename from product name."""
    clean = re.sub(r'[^\w\s-]', '', name.strip())
    clean = re.sub(r'[\s]+', '_', clean).lower()
    return clean[:80]


# ════════════════════════════════════════════
# FILE DISCOVERY
# ════════════════════════════════════════════

def discover_text_files():
    """Find all datasheet text files from Layer_1 and Layer_2."""
    files = []
    base = os.path.dirname(os.path.abspath(__file__))

    # Layer_2 local .txt files
    for f in sorted(os.listdir(base)):
        if f.endswith(".txt"):
            files.append(os.path.join(base, f))

    # Layer_1/extracted_text/ files
    layer1_dir = os.path.join(base, "..", "Layer_1", "extracted_text")
    if os.path.isdir(layer1_dir):
        for f in sorted(os.listdir(layer1_dir)):
            if f.endswith(".txt"):
                files.append(os.path.join(layer1_dir, f))

    return files


# ════════════════════════════════════════════
# SINGLE-FILE EXTRACTION (callable from other layers)
# ════════════════════════════════════════════

def extract_from_text(text, source_name="uploaded_file"):
    """
    Extract cameras from raw text. Callable from Layer 9 agent or frontend.
    Returns list of camera dicts with Title Case keys.
    """
    chunks = chunk_by_pages(text)
    all_cameras = []

    for i, chunk in enumerate(chunks, 1):
        specs = extract_cameras_from_chunk(chunk, source_name, i, len(chunks))
        for cam in specs:
            cam_dict = camera_to_dict(cam)
            if cam_dict.get("Product Name"):
                all_cameras.append(cam_dict)
        if i < len(chunks):
            time.sleep(0.3)

    return deduplicate_cameras(all_cameras)


def extract_from_file(filepath):
    """Extract cameras from a text file. Callable from other layers."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return extract_from_text(text, os.path.basename(filepath))


# ════════════════════════════════════════════
# MAIN PIPELINE
# ════════════════════════════════════════════

def run_extraction(save_dir=None):
    """
    Run the full extraction pipeline.
    Returns all extracted cameras as a list of dicts.
    """
    if save_dir is None:
        save_dir = os.path.dirname(os.path.abspath(__file__))

    print("═" * 62)
    print("  DatasheetAI — Intelligent Specification Extraction Engine")
    print("  Model: GPT-4o-mini  │  Structured Output  │  Confidence AI")
    print("═" * 62)

    txt_files = discover_text_files()
    if not txt_files:
        print("\n❌ No text files found. Run Layer_1/read_pdf.py first.")
        return []

    print(f"\n📁 Discovered {len(txt_files)} datasheet source files:")
    for f in txt_files:
        size = os.path.getsize(f)
        print(f"   • {os.path.basename(f):40s}  {size:>8,} bytes")

    all_cameras = []
    total_api_calls = 0
    start_time = time.time()

    for txt_file in txt_files:
        fname = os.path.basename(txt_file)
        print(f"\n{'─' * 58}")
        print(f"📄 Processing: {fname}")

        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_by_pages(text)
        print(f"   📐 Split into {len(chunks)} chunk(s)")

        file_cameras = []
        for i, chunk in enumerate(chunks, 1):
            cameras = extract_cameras_from_chunk(chunk, fname, i, len(chunks))
            total_api_calls += 1
            for cam in cameras:
                cam_dict = camera_to_dict(cam)
                if cam_dict.get("Product Name"):
                    file_cameras.append(cam_dict)
            if i < len(chunks):
                time.sleep(0.3)

        # Deduplicate within file
        file_cameras = deduplicate_cameras(file_cameras)

        print(f"\n   ✅ {len(file_cameras)} unique cameras from {fname}")

        # Save individual JSON per camera
        for cam in file_cameras:
            name = cam.get("Product Name", "unknown")
            json_name = safe_filename(name) + ".json"
            json_path = os.path.join(save_dir, json_name)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(cam, f, indent=4, ensure_ascii=False)

            n_fields = count_fields(cam)
            scores = cam.get("confidence_scores", {})
            valid_scores = [v for v in scores.values() if v > 0]
            avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0
            print(f"   💾 {json_name:45s} {n_fields:2d} fields │ conf: {avg:.0%}")

        all_cameras.extend(file_cameras)

    # Global deduplication
    all_cameras = deduplicate_cameras(all_cameras)

    # Save master summary
    elapsed = time.time() - start_time
    summary = {
        "extraction_metadata": {
            "model": MODEL,
            "total_cameras": len(all_cameras),
            "total_api_calls": total_api_calls,
            "source_files": [os.path.basename(f) for f in txt_files],
            "elapsed_seconds": round(elapsed, 1),
        },
        "cameras": all_cameras,
    }
    summary_path = os.path.join(save_dir, "_extraction_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    print(f"\n{'═' * 62}")
    print(f"  ✅ EXTRACTION COMPLETE")
    print(f"     Cameras extracted:  {len(all_cameras)}")
    print(f"     API calls made:     {total_api_calls}")
    print(f"     Time elapsed:       {elapsed:.1f}s")
    print(f"     Summary:            _extraction_summary.json")
    print(f"{'═' * 62}")

    return all_cameras


# ════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════

if __name__ == "__main__":
    run_extraction()