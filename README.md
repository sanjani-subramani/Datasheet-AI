# 🤖 DatasheetAI — Industrial Camera Intelligence System

> *Reducing 3-5 days of manual engineering work to under 2 minutes using AI*

![Python](https://img.shields.io/badge/Python-3.12-blue)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange)
![AI](https://img.shields.io/badge/AI-Claude%20API-purple)
![Status](https://img.shields.io/badge/Status-Active-green)

---

## 🎯 The Problem

In industrial manufacturing, selecting the right camera for a conveyor 
inspection system requires an engineer to:

- Visit 10-15 manufacturer websites manually
- Download and read 50+ PDF datasheets
- Extract specifications by hand
- Convert units mentally (μm → mm, inches → mm)
- Run engineering calculations for every camera
- Compare everything in Excel

**This takes 3-5 days of skilled engineering time.**
One wrong decision = lakhs wasted on wrong equipment.

---

## 💡 The Solution

**DatasheetAI** is an end-to-end AI pipeline that automates the entire 
camera selection process — from raw PDF to ranked recommendation.
### Layer 9 — 🤖 Autonomous Agent *(Coming Soon)*
AI agent that handles incomplete requirements, asks intelligent 
follow-up questions, runs calculations, and delivers complete 
recommendation reports autonomously.

---

## 🚀 Quick Start

### Prerequisites
```bash
pip install pdfplumber mysql-connector-python
```

### MySQL Setup
```sql
CREATE DATABASE datasheetai;
```

### Run the Pipeline
```bash
# Step 1 — Ingest PDFs
cd Layer_1 && python read_pdf.py

# Step 2 — Extract specs
cd ../Layer_2 && python extract_specs.py

# Step 3 — Normalize
cd ../Layer_3 && python normalize.py

# Step 4 — Validate
cd ../Layer_4 && python validate.py

# Step 5 — Store in database
cd ../Layer_5 && python store.py

# Step 6 — Run calculations
cd ../Layer_6 && python calculate.py

# Step 7 — Get recommendations
cd ../Layer_7 && python recommend.py

# Step 8 — Chat with your database
cd ../Layer_8 && python chat.py
```

---

## 📊 Example Output

### Engineering Calculation
---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Core language |
| pdfplumber | PDF text extraction |
| MySQL | Structured database |
| Tkinter | Validation GUI |
| Claude API | AI extraction & chat *(upgrading)* |
| Streamlit | Web interface *(coming soon)* |
| Git + GitHub | Version control |

---

## 📁 Project Structure
---

## 🔮 Roadmap

- [x] PDF ingestion pipeline
- [x] Spec extraction engine
- [x] Data normalization
- [x] Human validation GUI
- [x] MySQL database storage
- [x] Engineering calculation engine
- [x] Recommendation & ranking engine
- [x] Basic chat assistant
- [ ] Claude API intelligent extraction
- [ ] Full RAG chat with Claude API
- [ ] Streamlit web frontend
- [ ] Autonomous agent (Layer 9)
- [ ] Web scraper for 5000+ cameras
- [ ] Vector database integration
- [ ] SaaS deployment

---

## 👩‍💻 Author

**Sanjani Subramani**  
GitHub: [@sanjani-subramani](https://github.com/sanjani-subramani)

---

## 📄 License

MIT License — feel free to use and contribute.

---

*Built with ❤️ to solve a real industrial engineering problem*
