"""
DatasheetAI — Layer 6: Engineering Calculation Engine
═════════════════════════════════════════════════════
Evaluates cameras against engineering requirements using
physics-based formulas. Supports PASS/FAIL grading and
is callable from the agent layer and tool-calling system.
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
# ENGINEERING FORMULAS
# ════════════════════════════════════════════

def calculate_min_frame_rate(conveyor_speed_ms, object_size_mm):
    """
    Minimum frame rate so camera captures every object.
    Formula: fps = (speed_m/s × 1000) / object_size_mm
    """
    return (conveyor_speed_ms * 1000) / object_size_mm


def calculate_required_resolution(object_size_mm, defect_size_mm, safety_factor=2):
    """
    Minimum pixels to detect the smallest defect.
    Formula: pixels = (object_size / defect_size) × safety_factor
    """
    return (object_size_mm / defect_size_mm) * safety_factor


def calculate_max_exposure(defect_size_mm, conveyor_speed_ms):
    """
    Maximum exposure time before motion blur exceeds defect size.
    Formula: exposure_s = defect_size_mm / (speed_m/s × 1000)
    """
    return defect_size_mm / (conveyor_speed_ms * 1000)


def calculate_fov(working_distance_mm, sensor_size_mm, focal_length_mm):
    """
    Field of View calculation.
    Formula: FOV = (sensor_size × working_distance) / focal_length
    """
    if focal_length_mm == 0:
        return 0
    return (sensor_size_mm * working_distance_mm) / focal_length_mm


def calculate_pixel_resolution(object_size_mm, camera_resolution_px, fov_mm):
    """
    Pixel resolution (mm/pixel) — how much real-world distance each pixel covers.
    """
    if camera_resolution_px == 0:
        return float('inf')
    if fov_mm == 0:
        return object_size_mm / camera_resolution_px
    return fov_mm / camera_resolution_px


# ════════════════════════════════════════════
# SPEC EXTRACTORS
# ════════════════════════════════════════════

def extract_fps(frame_rate_str):
    """Extract numeric FPS from string like '90 fps'."""
    try:
        return float(str(frame_rate_str).strip().split()[0])
    except:
        return 0


def extract_horizontal_pixels(resolution_str):
    """Extract horizontal pixel count from '2048 x 2048 pixels'."""
    try:
        parts = str(resolution_str).split("x")
        return int(parts[0].strip().split()[0])
    except:
        return 0


def extract_vertical_pixels(resolution_str):
    """Extract vertical pixel count."""
    try:
        parts = str(resolution_str).split("x")
        return int(parts[1].strip().split()[0])
    except:
        return 0


def extract_weight(weight_str):
    """Extract numeric weight in grams."""
    try:
        val = str(weight_str).lower().replace("g", "").strip()
        return float(val)
    except:
        return 0


def extract_power(power_str):
    """Extract numeric power in watts."""
    try:
        import re
        nums = re.findall(r'[\d.]+', str(power_str))
        return float(nums[0]) if nums else 0
    except:
        return 0


# ════════════════════════════════════════════
# CAMERA EVALUATION — Callable from Agent/Tools
# ════════════════════════════════════════════

def evaluate_cameras(requirements, cameras=None):
    """
    Evaluate cameras against engineering requirements.
    
    Args:
        requirements: dict with keys:
            - conveyor_speed_ms (float)
            - object_size_mm (float)
            - defect_size_mm (float)
            - working_distance_mm (float, optional)
        cameras: list of camera dicts (if None, loads from database)
    
    Returns:
        dict with 'requirements', 'calculated', and 'results' keys
    """
    # Load cameras from database if not provided
    if cameras is None:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cameras")
        cameras = cursor.fetchall()
        cursor.close()
        conn.close()

    # Calculate engineering thresholds
    conv_speed = requirements.get("conveyor_speed_ms", 1.0)
    obj_size = requirements.get("object_size_mm", 50)
    defect_size = requirements.get("defect_size_mm", requirements.get("crack_size_mm", 0.1))
    work_dist = requirements.get("working_distance_mm", 500)

    min_fps = calculate_min_frame_rate(conv_speed, obj_size)
    min_pixels = calculate_required_resolution(obj_size, defect_size)
    max_exposure = calculate_max_exposure(defect_size, conv_speed)

    calculated = {
        "min_frame_rate_fps": round(min_fps, 1),
        "min_resolution_pixels": round(min_pixels),
        "max_exposure_time_ms": round(max_exposure * 1000, 4),
    }

    # Evaluate each camera
    results = []
    for camera in cameras:
        cam_fps = extract_fps(camera.get("frame_rate", "0"))
        cam_h_pixels = extract_horizontal_pixels(camera.get("resolution", "0"))
        cam_v_pixels = extract_vertical_pixels(camera.get("resolution", "0"))
        total_pixels = cam_h_pixels * cam_v_pixels

        fps_pass = cam_fps >= min_fps
        resolution_pass = cam_h_pixels >= min_pixels

        # Extra checks
        fps_margin = cam_fps - min_fps if fps_pass else min_fps - cam_fps
        res_margin = cam_h_pixels - min_pixels if resolution_pass else min_pixels - cam_h_pixels
        fps_headroom_pct = round((fps_margin / min_fps) * 100, 1) if min_fps > 0 else 0

        overall_pass = fps_pass and resolution_pass

        reasons = []
        if not fps_pass:
            reasons.append(f"FPS too low: {cam_fps} < {min_fps:.0f} needed")
        if not resolution_pass:
            reasons.append(f"Resolution too low: {cam_h_pixels} < {min_pixels:.0f} needed")
        if overall_pass:
            reasons.append("All engineering criteria met")

        result = {
            "product_name": camera.get("product_name", camera.get("Product Name", "")),
            "manufacturer": camera.get("manufacturer", camera.get("Manufacturer", "")),
            "frame_rate": cam_fps,
            "resolution_h": cam_h_pixels,
            "resolution_v": cam_v_pixels,
            "total_megapixels": round(total_pixels / 1e6, 2),
            "fps_pass": fps_pass,
            "resolution_pass": resolution_pass,
            "overall_pass": overall_pass,
            "fps_margin": round(fps_margin, 1),
            "fps_headroom_pct": fps_headroom_pct,
            "resolution_margin": round(res_margin),
            "reasons": reasons,
        }
        results.append(result)

    # Sort: passing cameras first (by FPS margin), then failing
    results.sort(key=lambda x: (not x["overall_pass"], -x.get("fps_margin", 0)))

    passing = [r for r in results if r["overall_pass"]]
    failing = [r for r in results if not r["overall_pass"]]

    return {
        "requirements": requirements,
        "calculated": calculated,
        "results": results,
        "summary": {
            "total_cameras": len(results),
            "passing": len(passing),
            "failing": len(failing),
        }
    }


# ============================================
# CLI -- Run standalone
# ============================================

def _safe_print(msg=""):
    """Print that never crashes on Windows cp1252."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode())


def run_calculations():
    """Run calculations with default requirements."""
    _safe_print("=" * 58)
    _safe_print("  DatasheetAI -- Engineering Calculation Engine")
    _safe_print("=" * 58)

    requirements = {
        "conveyor_speed_ms": 3.0,
        "object_size_mm": 50,
        "defect_size_mm": 0.05,
        "working_distance_mm": 500,
    }

    _safe_print(f"\nRequirements:")
    _safe_print(f"   Conveyor Speed:     {requirements['conveyor_speed_ms']} m/s")
    _safe_print(f"   Object Size:        {requirements['object_size_mm']} mm")
    _safe_print(f"   Defect Size:        {requirements['defect_size_mm']} mm")
    _safe_print(f"   Working Distance:   {requirements['working_distance_mm']} mm")
    _safe_print("-" * 58)

    result = evaluate_cameras(requirements)
    calc = result["calculated"]

    _safe_print(f"\nCalculated Thresholds:")
    _safe_print(f"   Min Frame Rate:     {calc['min_frame_rate_fps']} fps")
    _safe_print(f"   Min Resolution:     {calc['min_resolution_pixels']} pixels")
    _safe_print(f"   Max Exposure:       {calc['max_exposure_time_ms']} ms")
    _safe_print("-" * 58)

    _safe_print(f"\nCamera Evaluation:")
    for r in result["results"]:
        status = "[PASS]" if r["overall_pass"] else "[FAIL]"
        _safe_print(f"\n  {status}  {r['product_name']} ({r['manufacturer']})")
        _safe_print(f"         FPS: {r['frame_rate']}  (need {calc['min_frame_rate_fps']})")
        _safe_print(f"         Res: {r['resolution_h']} px  (need {calc['min_resolution_pixels']})")
        if r["overall_pass"]:
            _safe_print(f"         Headroom: +{r['fps_headroom_pct']}% FPS margin")

    # Save results
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calculation_results.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    s = result["summary"]
    _safe_print(f"\n{'=' * 58}")
    _safe_print(f"  {s['passing']} cameras PASS  |  {s['failing']} cameras FAIL")
    _safe_print(f"  Results saved to calculation_results.json")
    _safe_print(f"{'=' * 58}")

    return result


if __name__ == "__main__":
    run_calculations()