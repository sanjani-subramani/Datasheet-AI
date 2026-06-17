"""
DatasheetAI — Layer 5: Database Storage Engine
═══════════════════════════════════════════════
Stores validated camera specifications into MySQL.
Supports extended schema with 14+ spec fields.
All credentials loaded from .env file.
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
# DATABASE OPERATIONS
# ════════════════════════════════════════════

def get_connection():
    """Get a MySQL database connection."""
    return mysql.connector.connect(**DB_CONFIG)


def create_table(cursor):
    """Create cameras table with extended schema."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_name VARCHAR(150),
            manufacturer VARCHAR(100),
            resolution VARCHAR(80),
            frame_rate VARCHAR(50),
            pixel_size VARCHAR(50),
            sensor_size VARCHAR(50),
            sensor_technology VARCHAR(100),
            interface VARCHAR(80),
            bit_depth VARCHAR(50),
            weight VARCHAR(50),
            operating_temperature VARCHAR(80),
            power_consumption VARCHAR(50),
            lens_mount VARCHAR(50),
            sensor_name VARCHAR(100),
            confidence_avg FLOAT DEFAULT 0.0,
            source_file VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def ensure_columns(cursor):
    """Add new columns if they don't exist (for upgrades)."""
    new_columns = {
        "sensor_technology": "VARCHAR(100)",
        "operating_temperature": "VARCHAR(80)",
        "power_consumption": "VARCHAR(50)",
        "lens_mount": "VARCHAR(50)",
        "sensor_name": "VARCHAR(100)",
        "confidence_avg": "FLOAT DEFAULT 0.0",
        "source_file": "VARCHAR(200)",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }
    # Get existing columns
    cursor.execute("DESCRIBE cameras")
    existing = {row[0] for row in cursor.fetchall()}

    for col_name, col_type in new_columns.items():
        if col_name not in existing:
            try:
                cursor.execute(f"ALTER TABLE cameras ADD COLUMN {col_name} {col_type}")
                print(f"   [+] Added column: {col_name}")
            except Exception as e:
                pass  # Column might already exist


def insert_camera(cursor, camera, source="validated"):
    """Insert a single camera into the database."""
    # Calculate average confidence
    conf = camera.get("confidence_scores", {})
    valid_scores = [v for v in conf.values() if isinstance(v, (int, float)) and v > 0]
    avg_conf = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

    cursor.execute("""
        INSERT INTO cameras (
            product_name, manufacturer, resolution,
            frame_rate, pixel_size, sensor_size,
            sensor_technology, interface, bit_depth,
            weight, operating_temperature, power_consumption,
            lens_mount, sensor_name, confidence_avg, source_file
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        camera.get("Product Name", ""),
        camera.get("Manufacturer", ""),
        camera.get("Resolution", ""),
        camera.get("Frame Rate", ""),
        camera.get("Pixel Size", ""),
        camera.get("Sensor Size", ""),
        camera.get("Sensor Technology", ""),
        camera.get("Interface", ""),
        camera.get("Bit Depth", ""),
        camera.get("Weight", ""),
        camera.get("Operating Temperature", ""),
        camera.get("Power Consumption", ""),
        camera.get("Lens Mount", ""),
        camera.get("Sensor Name", ""),
        round(avg_conf, 3),
        source,
    ))


def store_cameras(cameras, source="validated"):
    """Store a list of camera dicts into the database. Callable from other layers."""
    conn = get_connection()
    cursor = conn.cursor()

    create_table(cursor)
    ensure_columns(cursor)

    # Clear existing data
    cursor.execute("DELETE FROM cameras")

    for camera in cameras:
        insert_camera(cursor, camera, source)

    conn.commit()
    count = len(cameras)

    cursor.close()
    conn.close()
    return count


def get_all_cameras():
    """Retrieve all cameras from database. Callable from other layers."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cameras ORDER BY id")
    cameras = cursor.fetchall()
    cursor.close()
    conn.close()
    return cameras


# ============================================
# CLI -- Run standalone
# ============================================

def _safe_print(msg=""):
    """Print that never crashes on Windows cp1252."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode())


def run_store():
    """Load validated cameras and insert into MySQL."""
    _safe_print("=" * 55)
    _safe_print("  DatasheetAI -- Database Storage Engine")
    _safe_print("=" * 55)

    conn = get_connection()
    cursor = conn.cursor()
    _safe_print("[OK] Connected to MySQL database!")

    create_table(cursor)
    ensure_columns(cursor)
    _safe_print("[OK] Table schema ready!")

    # Load validated data
    input_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "Layer_4", "validated_cameras.json"
    )

    # Fallback to normalized data if validated doesn't exist
    if not os.path.exists(input_file):
        input_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "Layer_3", "normalized_cameras.json"
        )
        _safe_print("[WARN] No validated data found, using normalized data")

    with open(input_file, "r", encoding="utf-8") as f:
        cameras = json.load(f)

    _safe_print(f"[OK] Loaded {len(cameras)} cameras from {os.path.basename(input_file)}")

    # Clear and re-insert
    cursor.execute("DELETE FROM cameras")

    for camera in cameras:
        insert_camera(cursor, camera, os.path.basename(input_file))

    conn.commit()
    _safe_print(f"[OK] {len(cameras)} cameras inserted into database!")

    # Verify
    cursor.execute("SELECT id, product_name, manufacturer, frame_rate FROM cameras")
    rows = cursor.fetchall()

    _safe_print(f"\n{'-' * 55}")
    _safe_print("Cameras in database:")
    _safe_print(f"{'-' * 55}")
    for row in rows:
        _safe_print(f"   ID: {row[0]:3d} | {row[1]:30s} | {row[2]:10s} | {row[3]}")

    cursor.close()
    conn.close()
    _safe_print(f"\n[OK] Done! Database connection closed.")


if __name__ == "__main__":
    run_store()