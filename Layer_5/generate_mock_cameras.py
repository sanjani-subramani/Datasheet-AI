"""
DatasheetAI — Layer 5: Mock Camera Generator
═════════════════════════════════════════════
Generates exactly 1000 unique, realistic industrial camera models with 
varying resolutions, frame rates, and configurations to demonstrate platform scale.
Stores them in MySQL and saves to Layer_4/validated_cameras.json, then rebuilds vector store.
"""

import os
import sys
import json
import random
import mysql.connector
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "datasheetai",
}

# Base camera data options
MANUFACTURERS = [
    "Basler", "FLIR", "Sony", "Allied Vision", "Baumer",
    "Teledyne DALSA", "Lucid Vision", "IDS Imaging", "Keyence", "Cognex"
]

SERIES = {
    "Basler": ["ace", "ace 2", "boost", "dart", "pulse"],
    "FLIR": ["Blackfly S", "Chameleon3", "Firefly DL", "Oryx"],
    "Sony": ["XCG-CG", "XCG-CP", "XCL-SG", "XCU-CG"],
    "Allied Vision": ["Alvium", "Mako", "Manta", "Prosilica GT"],
    "Baumer": ["CX Series", "EX Series", "LX Series", "QX Series"],
    "Teledyne DALSA": ["Genie Nano", "Falcon4", "Linea", "Linea Lite"],
    "Lucid Vision": ["Triton", "Phoenix", "Atlas", "Helios"],
    "IDS Imaging": ["uEye CP", "uEye LE", "uEye SE", "uEye FA"],
    "Keyence": ["CA-H", "CA-HX", "CV-H", "CV-X"],
    "Cognex": ["CIC Series", "In-Sight 8000", "In-Sight 9000"]
}

INTERFACES = ["USB 3.0", "GigE", "10 GigE", "CoaXPress", "Camera Link", "5 GigE"]

RESOLUTIONS = [
    (640, 480, "0.3 MP"),
    (1280, 720, "0.9 MP"),
    (1280, 960, "1.2 MP"),
    (1600, 1200, "1.9 MP"),
    (1920, 1080, "2.1 MP"),
    (1920, 1200, "2.3 MP"),
    (2048, 1536, "3.1 MP"),
    (2048, 2048, "4.2 MP"),
    (2448, 2048, "5.0 MP"),
    (2592, 1944, "5.0 MP"),
    (3088, 2076, "6.4 MP"),
    (3840, 2160, "8.3 MP"),
    (4096, 2160, "8.8 MP"),
    (4096, 3000, "12.3 MP"),
    (5120, 3840, "19.7 MP"),
    (5472, 3648, "20.0 MP"),
    (6576, 4384, "28.8 MP"),
    (7920, 6004, "47.5 MP"),
    (9344, 7000, "65.4 MP")
]

SENSORS = [
    ("IMX174", "1/1.2\"", "CMOS", 5.86),
    ("IMX249", "1/1.2\"", "CMOS", 5.86),
    ("IMX250", "2/3\"", "CMOS", 3.45),
    ("IMX252", "1/1.8\"", "CMOS", 3.45),
    ("IMX264", "2/3\"", "CMOS", 3.45),
    ("IMX265", "1/1.8\"", "CMOS", 3.45),
    ("IMX273", "1/2.9\"", "CMOS", 3.45),
    ("IMX287", "1/2.9\"", "CMOS", 6.9),
    ("IMX304", "1.1\"", "CMOS", 3.45),
    ("IMX392", "1/2.3\"", "CMOS", 3.45),
    ("IMX420", "1.1\"", "CMOS", 4.5),
    ("IMX428", "1.1\"", "CMOS", 4.5),
    ("IMX540", "1.2\"", "CMOS", 2.74),
    ("IMX541", "1.1\"", "CMOS", 2.74),
    ("IMX542", "1.1\"", "CMOS", 2.74),
    ("IMX545", "1/1.1\"", "CMOS", 2.74),
    ("IMX546", "1/1.1\"", "CMOS", 2.74),
    ("IMX547", "1/1.8\"", "CMOS", 2.74),
    ("Python 300", "1/4\"", "CMOS", 4.8),
    ("Python 5000", "1\"", "CMOS", 4.8),
    ("GMAX0505", "1.1\"", "CMOS", 2.5),
    ("GMAX2509", "2/3\"", "CMOS", 2.5)
]

LENS_MOUNTS = ["C-mount", "CS-mount", "F-mount", "M42-mount"]
SHUTTERS = ["Global Shutter CMOS", "Rolling Shutter CMOS"]


def generate_mock_cameras(count=1000):
    print(f"Generating {count} unique camera models...")
    cameras = []
    
    # We always include our 3 core real cameras first for backward compatibility and RAG stability
    real_cameras = [
        {
            "Product Name": "acA2040-90um",
            "Manufacturer": "Basler",
            "Resolution": "2048 x 2048 pixels",
            "Frame Rate": "90 fps",
            "Pixel Size": "0.0055 mm",
            "Sensor Size": "25.4 mm",
            "Sensor Technology": "Global Shutter CMOS",
            "Interface": "USB 3.0",
            "Bit Depth": "12 bit",
            "Weight": "40 g",
            "Operating Temperature": "0 to 50 C",
            "Power Consumption": "3.0 W",
            "Lens Mount": "C-mount",
            "Sensor Name": "Sony IMX250"
        },
        {
            "Product Name": "BFS-U3-51S5C",
            "Manufacturer": "FLIR",
            "Resolution": "2448 x 2048 pixels",
            "Frame Rate": "75 fps",
            "Pixel Size": "0.00345 mm",
            "Sensor Size": "11.1 mm",
            "Sensor Technology": "Global Shutter CMOS",
            "Interface": "USB 3.0",
            "Bit Depth": "12 bit",
            "Weight": "36 g",
            "Operating Temperature": "0 to 50 C",
            "Power Consumption": "3.0 W",
            "Lens Mount": "C-mount",
            "Sensor Name": "Sony IMX264"
        },
        {
            "Product Name": "XCG-CG510",
            "Manufacturer": "Sony",
            "Resolution": "2448 x 2048 pixels",
            "Frame Rate": "23 fps",
            "Pixel Size": "0.00345 mm",
            "Sensor Size": "11.1 mm",
            "Sensor Technology": "Global Shutter CMOS",
            "Interface": "GigE",
            "Bit Depth": "12 bit",
            "Weight": "50 g",
            "Operating Temperature": "-5 to 45 C",
            "Power Consumption": "3.0 W",
            "Lens Mount": "C-mount",
            "Sensor Name": "Sony IMX264"
        }
    ]
    
    for cam in real_cameras:
        cam["confidence_scores"] = {k: 1.0 for k in cam.keys()}
        cameras.append(cam)

    # Generate remaining 997 cameras
    generated_names = {"aca2040-90um", "bfs-u3-51s5c", "xcg-cg510"}
    
    while len(cameras) < count:
        mfg = random.choice(MANUFACTURERS)
        series_name = random.choice(SERIES[mfg])
        res_info = random.choice(RESOLUTIONS)
        sensor_info = random.choice(SENSORS)
        
        res_w, res_h, res_mp = res_info
        sensor_model, optical_size, tech, px_size_um = sensor_info
        
        # Calculate a realistic frame rate
        # Lower resolution & faster interface = higher frame rate
        pixels = res_w * res_h
        base_rate = 500000000 / pixels  # base multiplier
        
        # Interface speed factors
        iface = random.choice(INTERFACES)
        if iface == "USB 3.0":
            iface_factor = random.uniform(0.8, 1.2)
        elif iface == "GigE":
            iface_factor = random.uniform(0.15, 0.3)
        elif iface == "5 GigE":
            iface_factor = random.uniform(0.5, 0.8)
        elif iface == "10 GigE":
            iface_factor = random.uniform(1.0, 1.5)
        elif iface == "CoaXPress":
            iface_factor = random.uniform(1.5, 3.0)
        else: # Camera Link
            iface_factor = random.uniform(1.0, 2.0)
            
        fps = int(max(5, min(1000, base_rate * iface_factor)))
        
        # Create a unique product code
        res_code = f"{res_w // 100}x{res_h // 100}"
        fps_code = f"{fps}"
        sensor_suffix = "m" if random.random() > 0.4 else "c"  # mono vs color
        
        if mfg == "Basler":
            name = f"acA{res_w}-{fps_code}u{sensor_suffix}"
        elif mfg == "FLIR":
            name = f"BFS-U3-{res_mp.split()[0]}S{random.randint(1,9)}{sensor_suffix.upper()}"
        elif mfg == "Sony":
            name = f"XCG-CG{res_w // 100}{random.randint(10,99)}"
        elif mfg == "Allied Vision":
            name = f"Alvium {res_w}-{fps_code}{sensor_suffix}"
        else:
            name = f"{series_name} {res_code}-{fps_code}{sensor_suffix}"
            
        name_lower = name.lower()
        if name_lower in generated_names:
            continue
            
        generated_names.add(name_lower)
        
        # Convert pixel size to mm for calculation engine compatibility
        pixel_size_mm = f"{px_size_um / 1000:.5f} mm"
        
        weight = f"{random.randint(25, 350)} g"
        power = f"{random.uniform(1.2, 8.5):.1f} W"
        bit_depth = f"{random.choice([8, 10, 12, 14])} bit"
        temp = f"{random.choice([0, -10, -20])} to {random.choice([45, 50, 60, 65])} C"
        lens_mount = random.choice(LENS_MOUNTS)
        shutter = random.choice(SHUTTERS)
        
        camera = {
            "Product Name": name,
            "Manufacturer": mfg,
            "Resolution": f"{res_w} x {res_h} pixels",
            "Frame Rate": f"{fps} fps",
            "Pixel Size": pixel_size_mm,
            "Sensor Size": optical_size,
            "Sensor Technology": shutter,
            "Interface": iface,
            "Bit Depth": bit_depth,
            "Weight": weight,
            "Operating Temperature": temp,
            "Power Consumption": power,
            "Lens Mount": lens_mount,
            "Sensor Name": f"Sony {sensor_model}" if "IMX" in sensor_model else sensor_model
        }
        camera["confidence_scores"] = {k: round(random.uniform(0.95, 1.00), 2) for k in camera.keys()}
        cameras.append(camera)
        
    return cameras


def main():
    print("=" * 60)
    print("  DatasheetAI — Populating 1000 Camera Models")
    print("=" * 60)
    
    # Generate 1000 cameras
    cameras = generate_mock_cameras(1000)
    
    # Save to validated_cameras.json (Layer 4)
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Layer_4"))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "validated_cameras.json")
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(cameras, f, indent=4)
    print(f"[OK] Saved {len(cameras)} cameras to {out_file}")
    
    # Store in MySQL DB
    from store import store_cameras
    print("Writing to MySQL database...")
    db_count = store_cameras(cameras, source="mock_generator.py")
    print(f"[OK] Stored {db_count} cameras in MySQL 'cameras' table!")
    
    # Reindex Vector Store
    from Layer_8.vector_store import build_vector_store
    print("Rebuilding Vector Store (Batched Embeddings)...")
    build_vector_store()
    print("[OK] Vector Store reindexed successfully!")
    
    print("\n[OK] Scaling Complete! 1000 cameras successfully populated.")


if __name__ == "__main__":
    main()
