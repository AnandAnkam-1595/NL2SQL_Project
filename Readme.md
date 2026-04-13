# NL2SQL Clinic Management System

An AI-powered Natural Language to SQL system built with Vanna 2.0, FastAPI, and Groq LLM.
Ask questions in plain English and get SQL queries + results from a clinic database.

---

## Tech Stack

- **Vanna 2.0** — Agent-based NL2SQL framework
- **Groq (llama-3.3-70b-versatile)** — Free cloud LLM provider
- **FastAPI** — REST API framework
- **SQLite** — Database
- **Plotly** — Chart generation
- **Pandas** — Data processing

---

## LLM Provider

This project uses **Groq** (Option B) with the `llama-3.3-70b-versatile` model.
Groq is free, fast, and requires no local GPU or API cost.

Get a free Groq API key at: https://console.groq.com

---

## Project Structure

```
NL2SQL_Project/
  setup_database.py    # Creates schema + inserts dummy data
  seed_memory.py       # Seeds agent memory with 15 Q&A pairs
  vanna_setup.py       # Vanna 2.0 Agent initialization
  main.py              # FastAPI application
  requirements.txt     # All dependencies
  README.md            # This file
  RESULTS.md           # Test results for 20 questions
  clinic.db            # Generated SQLite database
  .env                 # API keys (not committed to git)
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/NL2SQL_Project.git
cd NL2SQL_Project
```

### 2. Create virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key at: https://console.groq.com

### 5. Create the database

```bash
python setup_database.py
```

Expected output:
```
Created 200 patients, 15 doctors, 500 appointments, 350 treatments, 300 invoices
```

### 6. Seed agent memory

```bash
python seed_memory.py
```

Expected output:
```
  Seeded: How many patients do we have?
  Seeded: List all doctors and their specializations
  ...
Memory seeded with 15 examples!
```

### 7. Start the API server

```bash
uvicorn main:app --reload --port 8000
```

---

## Accessing the API

Once the server is running:

| URL | Description |
|---|---|
| http://localhost:8000/docs | ✅ Swagger UI — use this to test all endpoints |
| http://localhost:8000/health | ✅ Health check endpoint |
| http://localhost:8000/chat | ✅ POST endpoint (use via Swagger or curl) |
| http://localhost:8000 | ⚠️ Shows "Not Found" — this is normal, no root route |

> **Important:** Always open **http://localhost:8000/docs** to interact with the API.
> The root URL `/` intentionally returns 404 as there is no frontend at that path.

---

## Run All Steps at Once

```bash
pip install -r requirements.txt && python setup_database.py && python seed_memory.py && uvicorn main:app --port 8000
```

---

## API Documentation

### POST /chat

Ask a natural language question about the clinic database.

**Request body:**
```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

**Response body:**
```json
{
  "message": "Found 5 result(s).",
  "sql_query": "SELECT p.first_name, p.last_name, SUM(i.total_amount) as total_spending FROM patients p JOIN invoices i ON p.id = i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [
    ["Thomas", "Moore", 20964.12],
    ["Daniel", "Martinez", 20486.65]
  ],
  "row_count": 5,
  "chart": { "data": [...], "layout": {...} },
  "chart_type": "bar"
}
```

**Validation rules:**
- Question must not be empty
- Question must not exceed 500 characters
- Generated SQL must be SELECT only
- Forbidden keywords: INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, xp_, sp_, GRANT, REVOKE, SHUTDOWN
- System tables (sqlite_master, sqlite_sequence) are blocked

---

### GET /health

Check system status.

**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 15
}
```

---

## Example Questions to Try

```
How many patients do we have?
List all doctors and their specializations
Which doctor has the most appointments?
What is the total revenue?
Show revenue by doctor
Top 5 patients by spending
Show monthly appointment count for the past 6 months
Which city has the most patients?
List patients who visited more than 3 times
Show unpaid invoices
What percentage of appointments are no-shows?
Show the busiest day of the week for appointments
Revenue trend by month
Average appointment duration by doctor
List patients with overdue invoices
Compare revenue between departments
Show patient registration trend by month
```

---

## Architecture Overview

```
User Question (Natural Language)
          │
          ▼
  FastAPI /chat endpoint
          │
          ▼
  Input Validation
  (empty check, length check)
          │
          ▼
  Vanna 2.0 Agent
  (llama-3.3-70b via Groq)
          │
          ├── Search agent memory for similar Q&A pairs
          ├── Generate SQL using LLM + schema context
          └── Execute via RunSqlTool (SqliteRunner)
          │
          ▼
  SQL Validation
  (SELECT only, no dangerous keywords)
          │
          ▼
  Execute SQL on clinic.db
          │
          ▼
  Generate Plotly Chart (if applicable)
          │
          ▼
  Return JSON Response
```

---

## Database Schema

### patients
| Column | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto-increment |
| first_name | TEXT | Patient first name |
| last_name | TEXT | Patient last name |
| email | TEXT | Patient email (nullable) |
| phone | TEXT | Phone number (nullable) |
| date_of_birth | DATE | Birth date |
| gender | TEXT | M / F |
| city | TEXT | City name |
| registered_date | DATE | Registration date |

### doctors
| Column | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto-increment |
| name | TEXT | Doctor full name |
| specialization | TEXT | e.g., Dermatology, Cardiology |
| department | TEXT | Department name |
| phone | TEXT | Contact number (nullable) |

### appointments
| Column | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto-increment |
| patient_id | INTEGER | FK to patients.id |
| doctor_id | INTEGER | FK to doctors.id |
| appointment_date | DATETIME | When the appointment is |
| status | TEXT | Scheduled / Completed / Cancelled / No-Show |
| notes | TEXT | Optional notes (nullable) |

### treatments
| Column | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto-increment |
| appointment_id | INTEGER | FK to appointments.id |
| treatment_name | TEXT | Name of procedure |
| cost | REAL | Treatment cost |
| duration_minutes | INTEGER | How long it took |

### invoices
| Column | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY | Auto-increment |
| patient_id | INTEGER | FK to patients.id |
| invoice_date | DATE | When invoice was created |
| total_amount | REAL | Total billed |
| paid_amount | REAL | Amount paid |
| status | TEXT | Paid / Pending / Overdue |

---

## Known Limitations

- The root URL `/` returns 404 — use `/docs` for the Swagger UI
- Groq's tool-calling occasionally fails for very simple queries — a direct LLM fallback handles this
- SQLite string comparisons are case-sensitive — status values must match exactly (e.g., `No-Show` not `no-show`)
- Chart data uses Plotly's binary encoding (bdata) for large datasets

---

## Notes for Reviewers

- LLM provider: **Groq** (free tier, no cost incurred)
- Model: **llama-3.3-70b-versatile**
- No ChromaDB required — uses Vanna 2.0's built-in DemoAgentMemory
- All API keys stored in `.env` file — never hardcoded
- SQL validation runs before every query execution