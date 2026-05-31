import mysql.connector
import json

# ============================================
# CONNECT TO MYSQL
# ============================================

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Srisaibaba!1",  # ← replace with your MySQL password
    database="datasheetai"
)

cursor = connection.cursor(dictionary=True)
print("✅ Connected to database!")

# ============================================
# ENGINEERING REQUIREMENTS
# Input your requirements here
# ============================================

requirements = {
    "conveyor_speed_ms":   3.0,    # faster conveyor
    "object_size_mm":      50,     # smaller object
    "crack_size_mm":       0.05,   # smaller crack
    "working_distance_mm": 500,
}

print("\n📋 Requirements:")
print(f"  Conveyor Speed:    {requirements['conveyor_speed_ms']} m/s")
print(f"  Object Size:       {requirements['object_size_mm']} mm")
print(f"  Crack Size:        {requirements['crack_size_mm']} mm")
print(f"  Working Distance:  {requirements['working_distance_mm']} mm")
print("-----------------------------")

# ============================================
# ENGINEERING FORMULAS
# ============================================

def calculate_min_frame_rate(conveyor_speed_ms, object_size_mm):
    """
    Minimum frame rate needed so camera captures
    every object on the conveyor
    Formula: fps = (conveyor_speed_ms * 1000) / object_size_mm
    """
    return (conveyor_speed_ms * 1000) / object_size_mm

def calculate_required_resolution(object_size_mm, crack_size_mm):
    """
    Minimum pixels needed to detect the crack
    Formula: pixels = object_size / crack_size * 2 (safety factor)
    """
    return (object_size_mm / crack_size_mm) * 2

def calculate_exposure_time(crack_size_mm, conveyor_speed_ms):
    """
    Maximum exposure time before image blurs
    Formula: exposure = crack_size / conveyor_speed
    """
    conveyor_speed_mms = conveyor_speed_ms * 1000  # convert to mm/s
    return crack_size_mm / conveyor_speed_mms

def extract_resolution_pixels(resolution_str):
    """
    Extract horizontal pixel count from resolution string
    Example: "2048 x 2048 pixels" → 2048
    """
    try:
        parts = resolution_str.split("x")
        return int(parts[0].strip().split()[0])
    except:
        return 0

def extract_frame_rate(frame_rate_str):
    """
    Extract numeric frame rate from string
    Example: "90 fps" → 90
    """
    try:
        return float(frame_rate_str.strip().split()[0])
    except:
        return 0

# ============================================
# CALCULATE REQUIREMENTS
# ============================================

min_fps = calculate_min_frame_rate(
    requirements["conveyor_speed_ms"],
    requirements["object_size_mm"]
)

required_pixels = calculate_required_resolution(
    requirements["object_size_mm"],
    requirements["crack_size_mm"]
)

max_exposure = calculate_exposure_time(
    requirements["crack_size_mm"],
    requirements["conveyor_speed_ms"]
)

print(f"\n⚙️  Calculated Requirements:")
print(f"  Minimum Frame Rate needed:  {min_fps} fps")
print(f"  Minimum Resolution needed:  {required_pixels} pixels")
print(f"  Maximum Exposure Time:      {max_exposure*1000:.4f} ms")
print("-----------------------------")

# ============================================
# EVALUATE EACH CAMERA
# ============================================

cursor.execute("SELECT * FROM cameras")
cameras = cursor.fetchall()

results = []

print("\n📷 Camera Evaluation:")
print("-----------------------------")

for camera in cameras:
    camera_fps = extract_frame_rate(camera["frame_rate"])
    camera_pixels = extract_resolution_pixels(camera["resolution"])

    fps_pass = camera_fps >= min_fps
    resolution_pass = camera_pixels >= required_pixels

    overall_pass = fps_pass and resolution_pass

    status = "✅ PASS" if overall_pass else "❌ FAIL"

    reason = []
    if not fps_pass:
        reason.append(f"FPS too low ({camera_fps} < {min_fps} needed)")
    if not resolution_pass:
        reason.append(f"Resolution too low ({camera_pixels} < {required_pixels} needed)")
    if overall_pass:
        reason.append("All criteria met")

    result = {
        "product_name": camera["product_name"],
        "manufacturer": camera["manufacturer"],
        "frame_rate": camera_fps,
        "resolution_pixels": camera_pixels,
        "fps_pass": fps_pass,
        "resolution_pass": resolution_pass,
        "overall_pass": overall_pass,
        "reason": ", ".join(reason)
    }

    results.append(result)

    print(f"\n{status} {camera['product_name']} ({camera['manufacturer']})")
    print(f"       Frame Rate:  {camera_fps} fps  (need {min_fps})")
    print(f"       Resolution:  {camera_pixels} px  (need {required_pixels})")
    print(f"       Reason:      {result['reason']}")

# ============================================
# SAVE RESULTS
# ============================================

with open("calculation_results.json", "w") as f:
    json.dump(results, f, indent=4)

passing = [r for r in results if r["overall_pass"]]
failing = [r for r in results if not r["overall_pass"]]

print("\n-----------------------------")
print(f"✅ {len(passing)} cameras PASS")
print(f"❌ {len(failing)} cameras FAIL")
print("Results saved to calculation_results.json")

cursor.close()
connection.close()