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

# ============================================
# LOAD ALL CAMERAS INTO MEMORY
# ============================================

cursor.execute("SELECT * FROM cameras")
all_cameras = cursor.fetchall()

print("=" * 50)
print("  DatasheetAI — Camera Assistant")
print("=" * 50)
print(f"  {len(all_cameras)} cameras loaded in database")
print("  Type 'quit' to exit")
print("  Type 'help' to see example questions")
print("=" * 50)

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_all_cameras():
    return all_cameras

def search_by_manufacturer(name):
    return [c for c in all_cameras
            if name.lower() in c["manufacturer"].lower()]

def search_by_interface(interface):
    return [c for c in all_cameras
            if interface.lower() in c["interface"].lower()]

def filter_by_fps(min_fps):
    results = []
    for c in all_cameras:
        try:
            fps = float(c["frame_rate"].split()[0])
            if fps >= min_fps:
                results.append(c)
        except:
            pass
    return results

def find_fastest():
    fastest = None
    max_fps = 0
    for c in all_cameras:
        try:
            fps = float(c["frame_rate"].split()[0])
            if fps > max_fps:
                max_fps = fps
                fastest = c
        except:
            pass
    return fastest

def find_lightest():
    lightest = None
    min_weight = float("inf")
    for c in all_cameras:
        try:
            weight = float(c["weight"].replace("g", "").strip())
            if weight < min_weight:
                min_weight = weight
                lightest = c
        except:
            pass
    return lightest

def find_highest_resolution():
    best = None
    max_pixels = 0
    for c in all_cameras:
        try:
            pixels = int(c["resolution"].split("x")[0].strip().split()[0])
            if pixels > max_pixels:
                max_pixels = pixels
                best = c
        except:
            pass
    return best

def format_camera(c):
    return (f"  📷 {c['product_name']} ({c['manufacturer']})\n"
            f"     Frame Rate:  {c['frame_rate']}\n"
            f"     Resolution:  {c['resolution']}\n"
            f"     Interface:   {c['interface']}\n"
            f"     Pixel Size:  {c['pixel_size']}\n"
            f"     Weight:      {c['weight']}")

# ============================================
# QUERY UNDERSTANDING
# ============================================

def understand_query(query):
    query = query.lower().strip()

    # Help
    if query == "help":
        return """
Example questions you can ask:
  - list all cameras
  - show basler cameras
  - show flir cameras
  - show sony cameras
  - which cameras have frame rate above 60
  - which cameras have frame rate above 30
  - which camera is fastest
  - which camera is lightest
  - which camera has highest resolution
  - which cameras use usb
  - which cameras use gige
  - how many cameras are in the database
        """

    # List all
    if any(word in query for word in ["list all", "show all", "all cameras"]):
        cameras = get_all_cameras()
        response = f"Found {len(cameras)} cameras:\n\n"
        for c in cameras:
            response += format_camera(c) + "\n\n"
        return response

    # Count
    if any(word in query for word in ["how many", "count"]):
        return f"There are {len(all_cameras)} cameras in the database."

    # Fastest
    if any(word in query for word in ["fastest", "highest fps", "most fps"]):
        c = find_fastest()
        if c:
            return f"The fastest camera is:\n\n{format_camera(c)}"

    # Lightest
    if "lightest" in query or "least weight" in query:
        c = find_lightest()
        if c:
            return f"The lightest camera is:\n\n{format_camera(c)}"

    # Highest resolution
    if any(word in query for word in ["highest resolution", "best resolution", "most pixels"]):
        c = find_highest_resolution()
        if c:
            return f"The highest resolution camera is:\n\n{format_camera(c)}"

    # Filter by FPS
    if "frame rate above" in query or "fps above" in query or "frame rate over" in query:
        for word in query.split():
            try:
                min_fps = float(word)
                cameras = filter_by_fps(min_fps)
                if cameras:
                    response = f"Found {len(cameras)} cameras with frame rate above {min_fps} fps:\n\n"
                    for c in cameras:
                        response += format_camera(c) + "\n\n"
                    return response
                else:
                    return f"No cameras found with frame rate above {min_fps} fps."
            except:
                pass

    # Search by manufacturer
    for brand in ["basler", "flir", "sony"]:
        if brand in query:
            cameras = search_by_manufacturer(brand)
            if cameras:
                response = f"Found {len(cameras)} {brand.upper()} camera(s):\n\n"
                for c in cameras:
                    response += format_camera(c) + "\n\n"
                return response
            else:
                return f"No {brand.upper()} cameras found in database."

    # Search by interface
    if "usb" in query:
        cameras = search_by_interface("usb")
        if cameras:
            response = f"Found {len(cameras)} cameras with USB interface:\n\n"
            for c in cameras:
                response += format_camera(c) + "\n\n"
            return response

    if "gige" in query or "gigabit" in query:
        cameras = search_by_interface("gige")
        if cameras:
            response = f"Found {len(cameras)} cameras with GigE interface:\n\n"
            for c in cameras:
                response += format_camera(c) + "\n\n"
            return response

    # Default
    return ("I didn't understand that question.\n"
            "Type 'help' to see example questions.")

# ============================================
# CHAT LOOP
# ============================================

while True:
    print()
    user_input = input("You: ").strip()

    if user_input.lower() == "quit":
        print("Goodbye! 👋")
        break

    if not user_input:
        continue

    response = understand_query(user_input)
    print(f"\nAI: {response}")

cursor.close()
connection.close()