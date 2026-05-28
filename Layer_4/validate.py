import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

# ============================================
# LOAD NORMALIZED DATA
# ============================================

input_file = "../Layer_3/normalized_cameras.json"

with open(input_file, "r") as f:
    cameras = json.load(f)

# ============================================
# SMART CONFIDENCE SCORING
# ============================================

def get_confidence(key, value):
    value_str = str(value).strip()

    # Check for OCR mistakes
    ocr_mistakes = ["9O", "l", "O0", "0O", "Il"]
    if any(m in value_str for m in ocr_mistakes):
        return "LOW"

    # Check for missing values
    if value_str == "" or value_str == "None" or value_str == "N/A":
        return "MISSING"

    # Check for suspiciously short values
    if len(value_str) < 2:
        return "LOW"

    # Check for numeric fields that should have units
    numeric_fields = ["Frame Rate", "Pixel Size", "Sensor Size", "Weight"]
    if key in numeric_fields:
        has_number = any(char.isdigit() for char in value_str)
        if not has_number:
            return "LOW"

    return "HIGH"

# ============================================
# PRE-PROCESS — Auto approve HIGH confidence
# ============================================

def preprocess_cameras(cameras):
    results = []
    for camera in cameras:
        camera_result = {
            "auto_approved": {},
            "needs_review": {}
        }
        for key, value in camera.items():
            confidence = get_confidence(key, value)
            if confidence == "HIGH":
                camera_result["auto_approved"][key] = value
            else:
                camera_result["needs_review"][key] = {
                    "value": value,
                    "confidence": confidence
                }
        results.append(camera_result)
    return results

processed = preprocess_cameras(cameras)

# Count how many fields need review
total_review = sum(len(c["needs_review"]) for c in processed)
total_auto = sum(len(c["auto_approved"]) for c in processed)

# ============================================
# VALIDATION APP
# ============================================

class ValidationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DatasheetAI — Smart Validation")
        self.root.geometry("900x650")
        self.root.configure(bg="#1e1e2e")

        self.camera_index = 0
        self.validated_cameras = []
        self.current_entries = {}
        self.current_status = {}

        self.build_header()
        self.build_summary()
        self.build_table()
        self.build_buttons()
        self.load_camera()

    def build_header(self):
        frame = tk.Frame(self.root, bg="#181825", pady=10)
        frame.pack(fill="x")

        tk.Label(
            frame,
            text="DatasheetAI — Smart Validation Layer",
            font=("Helvetica", 16, "bold"),
            bg="#181825",
            fg="#cdd6f4"
        ).pack(side="left", padx=20)

        self.progress_label = tk.Label(
            frame,
            text="",
            font=("Helvetica", 11),
            bg="#181825",
            fg="#a6adc8"
        )
        self.progress_label.pack(side="right", padx=20)

    def build_summary(self):
        frame = tk.Frame(self.root, bg="#1e1e2e", pady=5)
        frame.pack(fill="x", padx=20)

        tk.Label(
            frame,
            text=f"✅ {total_auto} fields auto-approved    "
                 f"⚠️ {total_review} fields need your review",
            font=("Helvetica", 11),
            bg="#1e1e2e",
            fg="#a6e3a1"
        ).pack(side="left")

        self.camera_label = tk.Label(
            frame,
            text="",
            font=("Helvetica", 12, "bold"),
            bg="#1e1e2e",
            fg="#89b4fa"
        )
        self.camera_label.pack(side="right")

    def build_table(self):
        # Header
        header = tk.Frame(self.root, bg="#313244")
        header.pack(fill="x", padx=20, pady=5)

        for text, width in [
            ("Spec", 22),
            ("Extracted Value", 25),
            ("Issue", 15),
            ("Action", 20)
        ]:
            tk.Label(
                header,
                text=text,
                font=("Helvetica", 10, "bold"),
                bg="#313244",
                fg="#cdd6f4",
                width=width,
                anchor="w"
            ).pack(side="left", padx=5, pady=4)

        # Scrollable area
        self.canvas = tk.Canvas(
            self.root, bg="#1e1e2e",
            highlightthickness=0, height=350
        )
        scrollbar = ttk.Scrollbar(
            self.root, orient="vertical",
            command=self.canvas.yview
        )
        self.table_frame = tk.Frame(self.canvas, bg="#1e1e2e")

        self.table_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window(
            (0, 0), window=self.table_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both",
                        expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")

    def build_buttons(self):
        frame = tk.Frame(self.root, bg="#1e1e2e", pady=10)
        frame.pack(fill="x")

        tk.Button(
            frame,
            text="✅ Approve All Shown",
            font=("Helvetica", 11, "bold"),
            bg="#a6e3a1", fg="#1e1e2e",
            padx=15, pady=6,
            command=self.approve_all
        ).pack(side="left", padx=20)

        tk.Button(
            frame,
            text="⏭ Next Camera →",
            font=("Helvetica", 11, "bold"),
            bg="#89b4fa", fg="#1e1e2e",
            padx=15, pady=6,
            command=self.next_camera
        ).pack(side="left", padx=10)

        tk.Button(
            frame,
            text="💾 Save & Finish",
            font=("Helvetica", 11, "bold"),
            bg="#f38ba8", fg="#1e1e2e",
            padx=15, pady=6,
            command=self.save_final
        ).pack(side="right", padx=20)

    def load_camera(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        self.current_entries = {}
        self.current_status = {}

        camera_data = processed[self.camera_index]
        needs_review = camera_data["needs_review"]
        auto_approved = camera_data["auto_approved"]

        name = auto_approved.get(
            "Product Name",
            f"Camera {self.camera_index + 1}"
        )
        manufacturer = auto_approved.get("Manufacturer", "")

        self.camera_label.config(
            text=f"📷 {name} — {manufacturer}"
        )
        self.progress_label.config(
            text=f"Camera {self.camera_index + 1} of {len(cameras)}"
        )

        if not needs_review:
            tk.Label(
                self.table_frame,
                text="🎉 All fields auto-approved! No review needed.",
                font=("Helvetica", 12),
                bg="#1e1e2e",
                fg="#a6e3a1",
                pady=30
            ).pack()
            return

        for i, (key, info) in enumerate(needs_review.items()):
            value = info["value"]
            confidence = info["confidence"]

            row_bg = "#1e1e2e" if i % 2 == 0 else "#27273a"
            issue_color = "#ff4444" if confidence == "LOW" else "#ff8800"

            row = tk.Frame(self.table_frame, bg=row_bg)
            row.pack(fill="x", pady=2)

            # Spec name
            tk.Label(
                row, text=key,
                font=("Helvetica", 10),
                bg=row_bg, fg="#cdd6f4",
                width=22, anchor="w"
            ).pack(side="left", padx=5, pady=5)

            # Editable value
            entry = tk.Entry(
                row,
                font=("Helvetica", 10),
                width=25,
                bg="#313244",
                fg="#cdd6f4",
                insertbackground="white"
            )
            entry.insert(0, str(value))
            entry.pack(side="left", padx=5)
            self.current_entries[key] = entry

            # Issue badge
            tk.Label(
                row,
                text=f"⚠️ {confidence}",
                font=("Helvetica", 9, "bold"),
                bg=row_bg,
                fg=issue_color,
                width=15
            ).pack(side="left", padx=5)

            # Status label
            status = tk.Label(
                row,
                text="⏳ Pending",
                font=("Helvetica", 9),
                bg=row_bg,
                fg="#a6adc8",
                width=12
            )
            status.pack(side="left", padx=2)
            self.current_status[key] = status

            # Approve button
            tk.Button(
                row, text="✅",
                bg="#a6e3a1", fg="#1e1e2e",
                font=("Helvetica", 9),
                command=lambda k=key: self.approve_field(k)
            ).pack(side="left", padx=2)

            # Reject button
            tk.Button(
                row, text="❌",
                bg="#f38ba8", fg="#1e1e2e",
                font=("Helvetica", 9),
                command=lambda k=key: self.reject_field(k)
            ).pack(side="left", padx=2)

    def approve_field(self, key):
        self.current_status[key].config(
            text="✅ Approved", fg="#a6e3a1"
        )

    def reject_field(self, key):
        self.current_entries[key].delete(0, tk.END)
        self.current_entries[key].insert(0, "REJECTED")
        self.current_status[key].config(
            text="❌ Rejected", fg="#f38ba8"
        )

    def approve_all(self):
        for key in self.current_status:
            self.current_status[key].config(
                text="✅ Approved", fg="#a6e3a1"
            )

    def collect_current(self):
        camera_data = processed[self.camera_index]
        final = dict(camera_data["auto_approved"])
        for key, entry in self.current_entries.items():
            value = entry.get()
            if value != "REJECTED":
                final[key] = value
        return final

    def next_camera(self):
        self.validated_cameras.append(self.collect_current())
        self.camera_index += 1
        if self.camera_index < len(cameras):
            self.load_camera()
        else:
            self.save_final()

    def save_final(self):
        self.validated_cameras.append(self.collect_current())
        output_file = "validated_cameras.json"
        with open(output_file, "w") as f:
            json.dump(self.validated_cameras, f, indent=4)
        messagebox.showinfo(
            "Saved!",
            f"✅ {len(self.validated_cameras)} cameras validated!\n"
            f"Saved to {output_file}"
        )
        self.root.quit()

# ============================================
# RUN
# ============================================

root = tk.Tk()
app = ValidationApp(root)
root.mainloop()