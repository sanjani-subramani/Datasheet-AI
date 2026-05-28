import json
import os

# Folder where datasheet text files are
folder = "."

# Specs we want to find
specs_we_want = [
    "Product Name",
    "Manufacturer",
    "Resolution",
    "Frame Rate",
    "Max Capture Speed",
    "Pixel Size",
    "Sensor Pixel Size",
    "Sensor Size",
    "Optical Format",
    "Interface",
    "Bit Depth",
    "Output Bit Depth",
    "Weight"
]

# Find all .txt files in folder
txt_files = []
for file in os.listdir(folder):
    if file.endswith(".txt"):
        txt_files.append(file)

print(f"Found {len(txt_files)} datasheet files:")
for f in txt_files:
    print(f"  - {f}")
print("-----------------------------")

# Process each file
for txt_file in txt_files:
    print(f"\nExtracting from: {txt_file}")
    
    with open(txt_file, "r") as file:
        lines = file.readlines()

    extracted = {}

    for line in lines:
        for spec in specs_we_want:
            if spec in line:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    extracted[key] = value

    # Save JSON with same name as txt file
    json_filename = txt_file.replace(".txt", ".json")
    with open(json_filename, "w") as json_file:
        json.dump(extracted, json_file, indent=4)

    print(f"Saved to: {json_filename}")
    for key, value in extracted.items():
        print(f"  {key}: {value}")

print("\n-----------------------------")
print("All files processed!")