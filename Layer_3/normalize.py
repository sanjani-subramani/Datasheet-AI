"""
DatasheetAI — Layer 3: Intelligent Normalization Engine
════════════════════════════════════════════════════════
Normalizes vendor-specific field names to standard names,
converts units to a common system, and passes through
AI confidence scores from Layer 2.
"""

import json
import os
import re

# ════════════════════════════════════════════
# NORMALIZATION MAPS
# ════════════════════════════════════════════

# Map vendor-specific names → standard names
NAME_MAP = {
    "Max Capture Speed": "Frame Rate",
    "Maximum Frame Rate": "Frame Rate",
    "Max Frame Rate": "Frame Rate",
    "Sensor Pixel Size": "Pixel Size",
    "Pixel Pitch": "Pixel Size",
    "Optical Format": "Sensor Size",
    "Sensor Format": "Sensor Size",
    "Output Bit Depth": "Bit Depth",
    "ADC Resolution": "Bit Depth",
    "Data Interface": "Interface",
    "Communication": "Interface",
    "Camera Weight": "Weight",
    "Mass": "Weight",
    "Model": "Product Name",
    "Model Name": "Product Name",
    "Camera Model": "Product Name",
    "Brand": "Manufacturer",
    "Vendor": "Manufacturer",
    "Sensor Type": "Sensor Technology",
    "Imager Technology": "Sensor Technology",
    "Power": "Power Consumption",
    "Temp Range": "Operating Temperature",
    "Operating Temp": "Operating Temperature",
    "Mount": "Lens Mount",
    "Lens Type": "Lens Mount",
    "Sensor Model": "Sensor Name",
    "Imager": "Sensor Name",
}

# Keys to skip during normalization (metadata, not specs)
SKIP_KEYS = {"confidence_scores"}


# ════════════════════════════════════════════
# UNIT CONVERSION FUNCTIONS
# ════════════════════════════════════════════

def normalize_pixel_size(value):
    """Normalize pixel size to 'X.XX x X.XX um' format."""
    try:
        value = str(value).strip()
        # Handle 'µm', 'μm', 'um' variants
        value = value.replace("µm", "um").replace("μm", "um")
        # Extract numbers
        nums = re.findall(r'[\d.]+', value)
        if len(nums) >= 2:
            return f"{float(nums[0])} x {float(nums[1])} um"
        elif len(nums) == 1:
            return f"{float(nums[0])} x {float(nums[0])} um"
    except:
        pass
    return value


def normalize_sensor_size(value):
    """Normalize sensor size — keep fractional inch format."""
    try:
        value = str(value).strip().replace('"', 'inch').replace("''", "inch")
        # Already in standard format
        if "inch" in value.lower() or '"' in value:
            return value
        # Convert pure number to inch
        if re.match(r'^[\d./]+$', value.strip()):
            return f"{value.strip()} inch"
    except:
        pass
    return value


def normalize_frame_rate(value):
    """Standardize frame rate to 'XX fps' format."""
    try:
        value = str(value).strip()
        nums = re.findall(r'[\d.]+', value)
        if nums:
            fps = float(nums[0])
            return f"{int(fps)} fps" if fps == int(fps) else f"{fps} fps"
    except:
        pass
    return value


def normalize_resolution(value):
    """Standardize resolution to 'H x V pixels' format."""
    try:
        value = str(value).strip()
        nums = re.findall(r'\d+', value)
        if len(nums) >= 2:
            h, v = int(nums[0]), int(nums[1])
            return f"{h} x {v} pixels"
    except:
        pass
    return value


def normalize_weight(value):
    """Standardize weight to 'XX g' format."""
    try:
        value = str(value).strip()
        nums = re.findall(r'[\d.]+', value)
        if nums:
            weight = float(nums[0])
            # Convert kg to g
            if "kg" in value.lower():
                weight *= 1000
            return f"{int(weight)} g" if weight == int(weight) else f"{weight} g"
    except:
        pass
    return value


def normalize_power(value):
    """Standardize power to 'X.X W' format."""
    try:
        value = str(value).strip()
        nums = re.findall(r'[\d.]+', value)
        if nums:
            power = float(nums[0])
            return f"{power} W"
    except:
        pass
    return value


def normalize_interface(value):
    """Standardize interface names."""
    value = str(value).strip()
    mapping = {
        "usb 3.0": "USB 3.0",
        "usb3": "USB 3.0",
        "usb3 vision": "USB 3.0",
        "usb3vision": "USB 3.0",
        "gige": "GigE Vision",
        "gige vision": "GigE Vision",
        "gigabit ethernet": "GigE Vision",
        "camera link": "Camera Link",
        "cameralink": "Camera Link",
        "coaxpress": "CoaXPress",
    }
    lower = value.lower()
    for key, standard in mapping.items():
        if key in lower:
            return standard
    return value


# ════════════════════════════════════════════
# MAIN NORMALIZATION
# ════════════════════════════════════════════

def normalize_camera(data):
    """Normalize a single camera's specs dict. Returns normalized dict."""
    normalized = {}
    confidence = data.get("confidence_scores", {})

    for key, value in data.items():
        if key in SKIP_KEYS:
            continue

        # Step 1 — Normalize key name
        standard_key = NAME_MAP.get(key, key)

        # Step 2 — Normalize value/unit
        if standard_key == "Pixel Size":
            value = normalize_pixel_size(value)
        elif standard_key == "Sensor Size":
            value = normalize_sensor_size(value)
        elif standard_key == "Frame Rate":
            value = normalize_frame_rate(value)
        elif standard_key == "Resolution":
            value = normalize_resolution(value)
        elif standard_key == "Weight":
            value = normalize_weight(value)
        elif standard_key == "Power Consumption":
            value = normalize_power(value)
        elif standard_key == "Interface":
            value = normalize_interface(value)

        normalized[standard_key] = value

    # Pass through confidence scores (mapped to standard keys)
    if confidence:
        mapped_conf = {}
        for key, score in confidence.items():
            standard_key = NAME_MAP.get(key, key)
            mapped_conf[standard_key] = score
        normalized["confidence_scores"] = mapped_conf

    return normalized


def run_normalization():
    """Run normalization on all Layer_2 JSON files."""
    layer2_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Layer_2")
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "normalized_cameras.json")

    # Find all camera JSON files (skip metadata files starting with _)
    json_files = sorted([
        f for f in os.listdir(layer2_folder)
        if f.endswith(".json") and not f.startswith("_")
    ])

    print("═" * 55)
    print("  DatasheetAI — Normalization Engine")
    print("═" * 55)
    print(f"\n📁 Found {len(json_files)} camera JSON files in Layer_2/")
    print("─" * 55)

    all_cameras = []

    for json_file in json_files:
        filepath = os.path.join(layer2_folder, json_file)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"\n📄 Normalizing: {json_file}")

        normalized = normalize_camera(data)
        name = normalized.get("Product Name", json_file)

        # Show key transformations
        changes = 0
        for orig_key in data:
            if orig_key in SKIP_KEYS:
                continue
            std_key = NAME_MAP.get(orig_key, orig_key)
            orig_val = data[orig_key]
            norm_val = normalized.get(std_key, orig_val)
            if orig_key != std_key or str(orig_val) != str(norm_val):
                print(f"   {orig_key}: {orig_val}  →  {std_key}: {norm_val}")
                changes += 1

        if changes == 0:
            print(f"   ✅ Already normalized")

        all_cameras.append(normalized)

    # Save all normalized cameras
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_cameras, f, indent=4, ensure_ascii=False)

    print(f"\n{'═' * 55}")
    print(f"✅ {len(all_cameras)} cameras normalized!")
    print(f"   Saved to: {os.path.basename(output_file)}")
    print(f"{'═' * 55}")

    return all_cameras


if __name__ == "__main__":
    run_normalization()