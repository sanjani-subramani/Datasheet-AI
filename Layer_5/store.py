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

cursor = connection.cursor()
print("✅ Connected to MySQL database!")

# ============================================
# CREATE TABLE
# ============================================

cursor.execute("""
    CREATE TABLE IF NOT EXISTS cameras (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_name VARCHAR(100),
        manufacturer VARCHAR(100),
        resolution VARCHAR(50),
        frame_rate VARCHAR(50),
        pixel_size VARCHAR(50),
        sensor_size VARCHAR(50),
        interface VARCHAR(50),
        bit_depth VARCHAR(50),
        weight VARCHAR(50)
    )
""")

print("✅ Table created!")

# ============================================
# LOAD VALIDATED DATA
# ============================================

with open("../Layer_4/validated_cameras.json", "r") as f:
    cameras = json.load(f)

print(f"✅ Loaded {len(cameras)} cameras from validated data")

# ============================================
# INSERT CAMERAS INTO DATABASE
# ============================================

# Clear existing data first
cursor.execute("DELETE FROM cameras")

for camera in cameras:
    cursor.execute("""
        INSERT INTO cameras (
            product_name, manufacturer, resolution,
            frame_rate, pixel_size, sensor_size,
            interface, bit_depth, weight
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        camera.get("Product Name", ""),
        camera.get("Manufacturer", ""),
        camera.get("Resolution", ""),
        camera.get("Frame Rate", ""),
        camera.get("Pixel Size", ""),
        camera.get("Sensor Size", ""),
        camera.get("Interface", ""),
        camera.get("Bit Depth", ""),
        camera.get("Weight", "")
    ))

connection.commit()
print(f"✅ {len(cameras)} cameras inserted into database!")

# ============================================
# VERIFY — Read back from database
# ============================================

cursor.execute("SELECT * FROM cameras")
rows = cursor.fetchall()

print("\n-----------------------------")
print("Cameras in database:")
print("-----------------------------")
for row in rows:
    print(f"ID: {row[0]} | {row[1]} | {row[2]} | Frame Rate: {row[4]}")

cursor.close()
connection.close()
print("\n✅ Done! Database connection closed.")