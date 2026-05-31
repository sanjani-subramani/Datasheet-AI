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
# Change these based on your actual needs
# ============================================

requirements = {
    "conveyor_speed_ms":   3.0,
    "object_size_mm":      50,
    "crack_size_mm":       0.05,
    "working_distance_mm": 500,
}

# ============================================
# CALCULATE MINIMUM REQUIREMENTS
# ============================================

min_fps = (requirements["conveyor_speed_ms"] * 1000) / requirements["object_size_mm"]
min_pixels = (requirements["object_size_mm"] / requirements["crack_size_mm"]) * 2

print(f"\n📋 Minimum Requirements:")
print(f"   Frame Rate:  {min_fps} fps")
print(f"   Resolution:  {min_pixels} pixels")
print("-----------------------------")

# ============================================
# SCORING SYSTEM
# ============================================

def score_camera(camera, min_fps, min_pixels):
    """
    Score each camera out of 100
    Higher score = better fit for requirements
    """
    score = 0
    reasons = []
    penalties = []

    # Extract values
    try:
        camera_fps = float(camera["frame_rate"].split()[0])
    except:
        camera_fps = 0

    try:
        camera_pixels = int(camera["resolution"].split("x")[0].strip().split()[0])
    except:
        camera_pixels = 0

    # ── FPS Score (40 points) ──
    if camera_fps >= min_fps:
        fps_ratio = min_fps / camera_fps
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
        penalties.append(f"❌ FPS too low: {camera_fps} < {min_fps} needed")
        return 0, reasons, penalties

    # ── Resolution Score (40 points) ──
    if camera_pixels >= min_pixels:
        res_ratio = min_pixels / camera_pixels
        if res_ratio >= 0.8:
            score += 40
            reasons.append(f"✅ Resolution: {camera_pixels}px (perfect fit)")
        elif res_ratio >= 0.5:
            score += 35
            reasons.append(f"✅ Resolution: {camera_pixels}px (good fit)")
        else:
            score += 25
            reasons.append(f"✅ Resolution: {camera_pixels}px (overkill)")
    else:
        penalties.append(f"❌ Resolution too low: {camera_pixels} < {min_pixels} needed")
        return 0, reasons, penalties

    # ── Interface Score (10 points) ──
    interface = camera["interface"].lower()
    if "usb 3" in interface or "usb3" in interface:
        score += 10
        reasons.append("✅ Interface: USB 3.0 (fast, standard)")
    elif "gige" in interface:
        score += 8
        reasons.append("✅ Interface: GigE (good for long distance)")
    else:
        score += 5
        reasons.append(f"✅ Interface: {camera['interface']}")

    # ── Weight Score (10 points) ──
    try:
        weight = float(camera["weight"].replace("g", "").strip())
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

# ============================================
# EVALUATE AND RANK ALL CAMERAS
# ============================================

cursor.execute("SELECT * FROM cameras")
cameras = cursor.fetchall()

scored_cameras = []

for camera in cameras:
    score, reasons, penalties = score_camera(
        camera, min_fps, min_pixels
    )
    scored_cameras.append({
        "product_name": camera["product_name"],
        "manufacturer": camera["manufacturer"],
        "frame_rate": camera["frame_rate"],
        "resolution": camera["resolution"],
        "interface": camera["interface"],
        "weight": camera["weight"],
        "score": score,
        "reasons": reasons,
        "penalties": penalties,
        "passed": score > 0
    })

# Sort by score — highest first
scored_cameras.sort(key=lambda x: x["score"], reverse=True)

# ============================================
# DISPLAY RESULTS
# ============================================

passing = [c for c in scored_cameras if c["passed"]]
failing = [c for c in scored_cameras if not c["passed"]]

print("\n🏆 RECOMMENDATION RESULTS")
print("============================")

for rank, camera in enumerate(passing, 1):
    stars = "⭐" * min(5, max(1, round(camera["score"] / 20)))
    print(f"\nRank {rank}: {camera['product_name']} ({camera['manufacturer']})")
    print(f"        Score: {camera['score']}/100  {stars}")
    for reason in camera["reasons"]:
        print(f"        {reason}")

if failing:
    print("\n❌ ELIMINATED CAMERAS:")
    for camera in failing:
        print(f"\n   {camera['product_name']} ({camera['manufacturer']})")
        for penalty in camera["penalties"]:
            print(f"   {penalty}")

# ============================================
# SAVE RESULTS
# ============================================

with open("recommendations.json", "w") as f:
    json.dump(scored_cameras, f, indent=4)

print("\n============================")
print(f"✅ {len(passing)} cameras recommended")
print(f"❌ {len(failing)} cameras eliminated")
print("Results saved to recommendations.json")

cursor.close()
connection.close()