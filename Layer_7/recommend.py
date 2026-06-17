"""
DatasheetAI — Layer 7: Smart Camera Recommendation Engine
════════════════════════════════════════════════════════
Scores and ranks cameras against conveyor speed, object size, and defect sizes.
All database passwords loaded from .env. Exposes callable functions.
"""

import os
import json
import mysql.connector
from dotenv import load_dotenv

# ════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "datasheetai",
}


# ════════════════════════════════════════════
# SCORING SYSTEM
# ════════════════════════════════════════════

def score_camera(camera, min_fps, min_pixels):
    """
    Score each camera out of 100.
    Higher score = better fit for requirements.
    """
    score = 0
    reasons = []
    penalties = []

    # Get values (support both snake_case and Title Case keys)
    fps_val = camera.get("frame_rate", camera.get("Frame Rate", "0"))
    res_val = camera.get("resolution", camera.get("Resolution", "0"))
    interface_val = camera.get("interface", camera.get("Interface", ""))
    weight_val = camera.get("weight", camera.get("Weight", ""))

    # Parse Frame Rate
    try:
        camera_fps = float(str(fps_val).strip().split()[0])
    except:
        camera_fps = 0

    # Parse Resolution (width)
    try:
        camera_pixels = int(str(res_val).split("x")[0].strip().split()[0])
    except:
        camera_pixels = 0

    # ── FPS Score (40 points) ──
    if camera_fps >= min_fps:
        fps_ratio = min_fps / camera_fps if camera_fps > 0 else 0
        fps_score = 40 * fps_ratio
        # Bonus for being close to requirement (not too much overkill)
        if fps_ratio >= 0.8:
            fps_score = 40
            reasons.append(f"✅ FPS: {camera_fps} (perfect fit)")
        elif fps_ratio >= 0.5:
            fps_score = 35
            reasons.append(f"✅ FPS: {camera_fps} (good fit)")
        else:
            fps_score = 25
            reasons.append(f"✅ FPS: {camera_fps} (overkill — may cost more)")
        score += fps_score
    else:
        penalties.append(f"❌ FPS too low: {camera_fps} < {min_fps:.1f} needed")
        return 0, reasons, penalties

    # ── Resolution Score (40 points) ──
    if camera_pixels >= min_pixels:
        res_ratio = min_pixels / camera_pixels if camera_pixels > 0 else 0
        if res_ratio >= 0.8:
            score += 40
            reasons.append(f"✅ Resolution: {camera_pixels}px (perfect fit)")
        elif res_ratio >= 0.5:
            score += 35
            reasons.append(f"✅ Resolution: {camera_pixels}px (good fit)")
        else:
            score += 25
            reasons.append(f"✅ Resolution: {camera_pixels}px (overkill)")
        score += score * 0  # placeholder
    else:
        penalties.append(f"❌ Resolution too low: {camera_pixels} < {min_pixels:.0f} needed")
        return 0, reasons, penalties

    # ── Interface Score (10 points) ──
    interface = str(interface_val).lower()
    if "usb 3" in interface or "usb3" in interface:
        score += 10
        reasons.append("✅ Interface: USB 3.0 (fast, standard)")
    elif "gige" in interface:
        score += 8
        reasons.append("✅ Interface: GigE (good for long distance)")
    else:
        score += 5
        reasons.append(f"✅ Interface: {interface_val}")

    # ── Weight Score (10 points) ──
    try:
        weight = float(str(weight_val).replace("g", "").strip())
        if weight < 70:
            score += 10
            reasons.append(f"✅ Weight: {weight}g (lightweight)")
        elif weight < 100:
            score += 7
            reasons.append(f"✅ Weight: {weight}g (moderate)")
        else:
            score += 4
            reasons.append(f"⚠️ Weight: {weight}g (heavy)")
    except:
        score += 5

    return round(score), reasons, penalties


# ════════════════════════════════════════════
# CORE CALLABLE FUNCTION
# ════════════════════════════════════════════

def get_recommendations(requirements, cameras=None):
    """
    Score and rank cameras against engineering requirements.
    
    Args:
        requirements: dict containing speed and defect thresholds
        cameras: optional list of cameras (if None, queries MySQL)
    """
    conveyor_speed = requirements.get("conveyor_speed_ms", 3.0)
    object_size = requirements.get("object_size_mm", 50.0)
    crack_size = requirements.get("crack_size_mm", requirements.get("defect_size_mm", 0.05))

    # Minimum thresholds
    min_fps = (conveyor_speed * 1000) / object_size
    min_pixels = (object_size / crack_size) * 2

    # Load from database if not provided
    if cameras is None:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cameras")
        cameras = cursor.fetchall()
        cursor.close()
        conn.close()

    scored_cameras = []
    for camera in cameras:
        score, reasons, penalties = score_camera(camera, min_fps, min_pixels)
        scored_cameras.append({
            "product_name": camera.get("product_name", camera.get("Product Name", "")),
            "manufacturer": camera.get("manufacturer", camera.get("Manufacturer", "")),
            "frame_rate": camera.get("frame_rate", camera.get("Frame Rate", "")),
            "resolution": camera.get("resolution", camera.get("Resolution", "")),
            "interface": camera.get("interface", camera.get("Interface", "")),
            "weight": camera.get("weight", camera.get("Weight", "")),
            "score": score,
            "reasons": reasons,
            "penalties": penalties,
            "passed": score > 0
        })

    # Sort by score — highest first
    scored_cameras.sort(key=lambda x: x["score"], reverse=True)
    return scored_cameras


# ============================================
# CLI STANDALONE EXECUTION
# ============================================

def _safe_print(msg=""):
    """Print that never crashes on Windows cp1252."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode())


def run_recommendations():
    """Standalone CLI run using default requirements."""
    _safe_print("=" * 55)
    _safe_print("  DatasheetAI -- Camera Recommendation Engine")
    _safe_print("=" * 55)

    requirements = {
        "conveyor_speed_ms": 3.0,
        "object_size_mm": 50.0,
        "crack_size_mm": 0.05,
    }

    results = get_recommendations(requirements)
    passing = [c for c in results if c["passed"]]
    failing = [c for c in results if not c["passed"]]

    _safe_print("\nRANKED RECOMMENDATIONS:")
    for rank, camera in enumerate(passing, 1):
        _safe_print(f"\nRank {rank}: {camera['product_name']} ({camera['manufacturer']})")
        _safe_print(f"        Score: {camera['score']}/100")
        for reason in camera["reasons"]:
            _safe_print(f"        {reason}")

    if failing:
        _safe_print("\nELIMINATED CAMERAS:")
        for camera in failing:
            _safe_print(f"\n   {camera['product_name']} ({camera['manufacturer']})")
            for penalty in camera["penalties"]:
                _safe_print(f"   {penalty}")

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recommendations.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    _safe_print(f"\n{'-' * 55}")
    _safe_print(f"[OK] {len(passing)} cameras recommended")
    _safe_print(f"[--] {len(failing)} cameras eliminated")
    _safe_print(f"Results saved to: recommendations.json")
    _safe_print("=" * 55)


if __name__ == "__main__":
    run_recommendations()