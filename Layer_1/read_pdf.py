import os
from pypdf import PdfReader

# Folder where PDFs are
folder = "."

# Folder where output text files will be saved
output_folder = "extracted_text"

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"Created folder: {output_folder}")

# Automatically find all PDF files
pdf_files = []
for file in os.listdir(folder):
    if file.endswith(".pdf"):
        pdf_files.append(file)

print(f"Found {len(pdf_files)} PDF files:")
for file in pdf_files:
    print(" -", file)
print("-----------------------------")

# Read each PDF one by one
for pdf_file in pdf_files:
    print(f"\nReading: {pdf_file}")
    reader = PdfReader(pdf_file)
    total_pages = len(reader.pages)
    print(f"Total pages: {total_pages}")

    # Save output inside extracted_text folder
    output_filename = os.path.join(output_folder, pdf_file + ".txt")
    with open(output_filename, "w", encoding="utf-8") as output_file:
        for page_number in range(total_pages):
            page = reader.pages[page_number]
            text = page.extract_text()
            output_file.write(f"--- Page {page_number + 1} ---\n")
            output_file.write(text)
            output_file.write("\n\n")

    print(f"Saved to: {output_filename}")

print("\n-----------------------------")
print("All PDFs processed successfully!")
print(f"All text files saved in: {output_folder}/")