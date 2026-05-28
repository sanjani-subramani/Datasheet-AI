import json

# Open the sample datasheet
with open("sample_datasheet.txt", "r") as file:
    lines = file.readlines()

print("Extracting specs...")
print("-----------------------------")

# List of specs we want to find
specs_we_want = [
    "Product Name",
    "Manufacturer",
    "Sensor",
    "Resolution",
    "Frame Rate",
    "Pixel Size",
    "Sensor Size",
    "Interface",
    "Bit Depth",
    "Weight",
    "Dimensions"
]

# Go through every line and find the specs we want
extracted = {}

for line in lines:
    for spec in specs_we_want:
        if spec in line:
            parts = line.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                extracted[key] = value

# Print what we found
print("Extracted Specifications:")
print("-----------------------------")
for key, value in extracted.items():
    print(f"{key}: {value}")

# Save extracted specs to a JSON file
with open("extracted_specs.json", "w") as json_file:
    json.dump(extracted, json_file, indent=4)

print("-----------------------------")
print("Specs saved to extracted_specs.json")