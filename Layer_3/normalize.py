import json
import os

# ============================================
# NORMALIZATION MAPS
# ============================================

# Map different vendor names → one standard name
name_map = {
    "Max Capture Speed": "Frame Rate",
    "Sensor Pixel Size": "Pixel Size",
    "Optical Format":    "Sensor Size",
    "Output Bit Depth":  "Bit Depth",
}

# ============================================
# UNIT CONVERSION FUNCTIONS
# ============================================

def convert_pixel_size(value):
    # Convert um to mm
    # Input example: "5.5 x 5.5 um" or "3.45 x 3.45 um"
    try:
        number = float(value.split("x")[0].strip().split()[0])
        mm = round(number / 1000, 6)
        return f"{mm} mm"
    except:
        return value

def convert_sensor_size(value):
    # Convert inches to mm
    # Input example: "1 inch" or "2/3 inch"
    try:
        value = value.strip()
        if "2/3" in value:
            inches = 2/3
        elif "1/2.5" in value:
            inches = 1/2.5
        elif "1/3" in value:
            inches = 1/3
        else:
            inches = float(value.split()[0])
        mm = round(inches * 25.4, 2)
        return f"{mm} mm"
    except:
        return value

def clean_frame_rate(value):
    # Standardize frame rate to just number + fps
    # Input: "90 fps" or "75 frames/sec" or "23 fps"
    try:
        number = float(value.strip().split()[0])
        return f"{int(number)} fps"
    except:
        return value

# ============================================
# MAIN NORMALIZATION
# ============================================

# Read all JSON files from Layer_2
layer2_folder = "../Layer_2"
json_files = []
for file in os.listdir(layer2_folder):
    if file.endswith(".json"):
        json_files.append(file)

print(f"Found {len(json_files)} camera JSON files")
print("-----------------------------")

all_cameras = []

for json_file in json_files:
    filepath = os.path.join(layer2_folder, json_file)
    
    with open(filepath, "r") as f:
        data = json.load(f)
    
    print(f"\nNormalizing: {json_file}")
    
    normalized = {}
    
    for key, value in data.items():
        # Step 1 — Normalize the name
        standard_key = name_map.get(key, key)
        
        # Step 2 — Normalize the value/unit
        if standard_key == "Pixel Size":
            value = convert_pixel_size(value)
        elif standard_key == "Sensor Size":
            value = convert_sensor_size(value)
        elif standard_key == "Frame Rate":
            value = clean_frame_rate(value)
        
        normalized[standard_key] = value
    
    print("  Before → After:")
    for key in data:
        standard_key = name_map.get(key, key)
        print(f"  {key}: {data[key]}  →  {standard_key}: {normalized[standard_key]}")
    
    all_cameras.append(normalized)

# Save all normalized cameras to one file
with open("normalized_cameras.json", "w") as f:
    json.dump(all_cameras, f, indent=4)

print("\n-----------------------------")
print(f"All {len(all_cameras)} cameras normalized!")
print("Saved to: normalized_cameras.json")