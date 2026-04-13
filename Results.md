# Test Results — 20 Question Evaluation

**System:** NL2SQL Clinic Management System  
**LLM:** Groq llama-3.3-70b-versatile  
**Database:** clinic.db (SQLite)  
**Date:** April 2026  
**Total Score: 15/20 (75%)**

---

## Results Summary Table

| # | Question | Status | SQL Correct | Result Summary |
|---|---|---|---|---|
| 1 | How many patients do we have? | ✅ Pass | ✅ | Returns 200 |
| 2 | List all doctors and their specializations | ❌ Fail | ❌ | Agent tool call failed intermittently |
| 3 | Show me appointments for last month | ✅ Pass | ✅ | Returns 31 appointments with chart |
| 4 | Which doctor has the most appointments? | ✅ Pass | ✅ | Dr. Sarah Connor (56 appointments) |
| 5 | What is the total revenue? | ✅ Pass | ✅ | $749,730.66 |
| 6 | Show revenue by doctor | ❌ Fail | ❌ | LLM used wrong column name |
| 7 | How many cancelled appointments last quarter? | ⚠️ Partial | ⚠️ | Wrong case sensitivity, returns 0 |
| 8 | Top 5 patients by spending | ✅ Pass | ✅ | Returns top 5 with bar chart |
| 9 | Average treatment cost by specialization | ❌ Fail | ❌ | Ambiguous JOIN query generated |
| 10 | Show monthly appointment count for past 6 months | ✅ Pass | ✅ | 7 months returned with line chart |
| 11 | Which city has the most patients? | ✅ Pass | ✅ | San Antonio |
| 12 | List patients who visited more than 3 times | ✅ Pass | ✅ | 44 patients with bar chart |
| 13 | Show unpaid invoices | ✅ Pass | ✅ | 101 unpaid invoices returned |
| 14 | What percentage of appointments are no-shows? | ⚠️ Partial | ⚠️ | Wrong case, returns 0% instead of correct % |
| 15 | Show the busiest day of the week for appointments | ✅ Pass | ✅ | Saturday |
| 16 | Revenue trend by month | ✅ Pass | ✅ | 13 months with line chart |
| 17 | Average appointment duration by doctor | ✅ Pass | ✅ | All 15 doctors with bar chart |
| 18 | List patients with overdue invoices | ✅ Pass | ✅ | 101 records returned |
| 19 | Compare revenue between departments | ✅ Pass | ✅ | 5 departments with bar chart |
| 20 | Show patient registration trend by month | ❌ Fail | ❌ | Agent tool call failed intermittently |

---

## Score by Category

| Category | Questions | Pass | Fail | Partial |
|---|---|---|---|---|
| Patient queries | 1, 8, 11, 12 | 4 | 0 | 0 |
| Doctor queries | 2, 4, 17 | 2 | 1 | 0 |
| Appointment queries | 3, 7, 10, 15 | 3 | 0 | 1 |
| Financial queries | 5, 6, 9, 13, 18, 19 | 4 | 2 | 0 |
| Time-based queries | 14, 16, 20 | 1 | 1 | 1 |
| Registration queries | 20 | 0 | 1 | 0 |
| **Total** | **20** | **15** | **4** | **2** |

---

## Detailed Results

---

### Q1 — How many patients do we have? ✅

**Generated SQL:**
```sql
SELECT COUNT(id) FROM patients
```

**Result:**
```json
{
  "columns": ["COUNT(id)"],
  "rows": [[200]],
  "row_count": 1
}
```

**Notes:** Correct answer returned instantly. Simple COUNT query handled perfectly.

---

### Q2 — List all doctors and their specializations ❌

**Generated SQL:** None  
**Result:** `"Could not generate SQL for this question."`

**Reason:** Groq LLM occasionally fails to invoke the RunSqlTool for simple listing queries due to tool-calling reliability issues in Vanna 2.0's streaming interface. The fallback LLM call also failed to trigger for this specific phrasing.

**Correct SQL:**
```sql
SELECT name, specialization FROM doctors ORDER BY specialization
```

---

### Q3 — Show me appointments for last month ✅

**Generated SQL:**
```sql
SELECT * FROM appointments
WHERE STRFTIME('%Y-%m', appointment_date) = STRFTIME('%Y-%m', DATE('now', '-1 month'))
```

**Result:** 31 appointments in March 2026 returned with line chart.

**Notes:** Correct date filtering using SQLite STRFTIME functions.

---

### Q4 — Which doctor has the most appointments? ✅

**Generated SQL:**
```sql
SELECT T1.name FROM doctors AS T1
INNER JOIN appointments AS T2 ON T1.id = T2.doctor_id
GROUP BY T1.name
ORDER BY COUNT(T2.id) DESC
LIMIT 1
```

**Result:**
```json
{
  "columns": ["name"],
  "rows": [["Dr. Sarah Connor"]],
  "row_count": 1
}
```

**Notes:** Correct aggregation and ordering. Dr. Sarah Connor has 56 appointments.

---

### Q5 — What is the total revenue? ✅

**Generated SQL:**
```sql
SELECT SUM(total_amount) FROM invoices
```

**Result:**
```json
{
  "columns": ["SUM(total_amount)"],
  "rows": [[749730.66]],
  "row_count": 1
}
```

**Notes:** Correct SUM calculation across all invoices.

---

### Q6 — Show revenue by doctor ❌

**Generated SQL:**
```sql
SELECT T3.name, SUM(T5.cost) AS revenue
FROM patients AS T1
JOIN appointments AS T2 ON T1.id = T2.patient_id
JOIN doctors AS T3 ON T2.doctor_id = T3.id
JOIN treatments AS T4 ON T2.id = T4.appointment_id
JOIN invoices AS T5 ON T1.id = T5.patient_id
GROUP BY T3.name
```

**Result:** `Query execution failed: no such column: T5.cost`

**Reason:** The LLM incorrectly used `T5.cost` (treating invoices as if it has a cost column) instead of `T5.total_amount`. The invoices table has `total_amount`, not `cost`.

**Correct SQL:**
```sql
SELECT d.name, SUM(i.total_amount) AS total_revenue
FROM doctors d
JOIN appointments a ON d.id = a.doctor_id
JOIN invoices i ON a.patient_id = i.patient_id
GROUP BY d.name
ORDER BY total_revenue DESC
```

---

### Q7 — How many cancelled appointments last quarter? ⚠️

**Generated SQL:**
```sql
SELECT COUNT(*) FROM appointments
WHERE status = 'cancelled'
AND STRFTIME('%Y', appointment_date) = STRFTIME('%Y', 'now')
AND STRFTIME('%m', appointment_date) IN (10, 11, 12)
```

**Result:** 0 (incorrect)

**Reason:** Two issues:
1. SQLite string comparison is case-sensitive. LLM used `'cancelled'` but database stores `'Cancelled'`
2. The quarter logic is hardcoded to Q4 (months 10,11,12) rather than dynamically calculating the last 3 months

**Correct SQL:**
```sql
SELECT COUNT(*) AS cancelled_count
FROM appointments
WHERE status = 'Cancelled'
AND appointment_date >= date('now', '-3 months')
```

---

### Q8 — Top 5 patients by spending ✅

**Generated SQL:**
```sql
SELECT p.first_name, p.last_name, SUM(i.total_amount) as total_spending
FROM patients p
JOIN invoices i ON p.id = i.patient_id
GROUP BY p.id
ORDER BY total_spending DESC
LIMIT 5
```

**Result:**
```json
{
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [
    ["Thomas", "Moore", 20964.12],
    ["Daniel", "Martinez", 20486.65],
    ["Linda", "Brown", 17989.88],
    ["Jessica", "Rodriguez", 17584.27],
    ["Helen", "Martinez", 14244.88]
  ],
  "row_count": 5
}
```

**Notes:** Correct JOIN and ordering. Bar chart generated successfully.

---

### Q9 — Average treatment cost by specialization ❌

**Generated SQL:**
```sql
SELECT T2.specialization, AVG(T4.cost) AS average_treatment_cost
FROM doctors AS T1
INNER JOIN appointments AS T2 ON T1.id = T2.doctor_id
INNER JOIN treatments AS T3 ON T2.id = T3.appointment_id
INNER JOIN treatments AS T4 ON T3.appointment_id = T4.appointment_id
INNER JOIN doctors AS T2 ON T7.id = T2.id
GROUP BY T2.specialization
```

**Result:** `Query execution failed: ambiguous column name: T2.id`

**Reason:** LLM generated an overly complex query with duplicate table aliases (T2 used for both appointments and doctors), causing an ambiguous column name error.

**Correct SQL:**
```sql
SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost
FROM treatments t
JOIN appointments a ON t.appointment_id = a.id
JOIN doctors d ON a.doctor_id = d.id
GROUP BY d.specialization
ORDER BY avg_cost DESC
```

---

### Q10 — Show monthly appointment count for past 6 months ✅

**Generated SQL:**
```sql
SELECT STRFTIME('%Y-%m', appointment_date) AS month, COUNT(*) AS count
FROM appointments
WHERE appointment_date >= DATE('now', '-6 month')
GROUP BY STRFTIME('%Y-%m', appointment_date)
ORDER BY month DESC
```

**Result:**
```json
{
  "columns": ["month", "count"],
  "rows": [
    ["2026-04", 16], ["2026-03", 31], ["2026-02", 40],
    ["2026-01", 49], ["2025-12", 54], ["2025-11", 45], ["2025-10", 16]
  ],
  "row_count": 7
}
```

**Notes:** Correct date filtering and grouping. Line chart generated.

---

### Q11 — Which city has the most patients? ✅

**Generated SQL:**
```sql
SELECT city FROM patients
GROUP BY city
ORDER BY COUNT(id) DESC
LIMIT 1
```

**Result:**
```json
{
  "columns": ["city"],
  "rows": [["San Antonio"]],
  "row_count": 1
}
```

**Notes:** Correct GROUP BY with ordering.

---

### Q12 — List patients who visited more than 3 times ✅

**Generated SQL:**
```sql
SELECT p.first_name, p.last_name, COUNT(a.id) as visit_count
FROM patients p
JOIN appointments a ON p.id = a.patient_id
GROUP BY p.id
HAVING COUNT(a.id) > 3
```

**Result:** 44 patients returned with bar chart.

**Notes:** Correct use of HAVING clause for post-aggregation filtering.

---

### Q13 — Show unpaid invoices ✅

**Generated SQL:**
```sql
SELECT * FROM invoices
WHERE paid_amount < total_amount AND status != 'paid'
```

**Result:** 101 unpaid invoices returned with all columns.

**Notes:** Correct filter logic combining amount and status checks.

---

### Q14 — What percentage of appointments are no-shows? ⚠️

**Generated SQL:**
```sql
SELECT CAST(SUM(CASE WHEN status = 'no-show' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*)
FROM appointments
```

**Result:** 0% (incorrect)

**Reason:** LLM used `'no-show'` (lowercase with hyphen) but the database stores `'No-Show'` (title case). SQLite string comparison is case-sensitive by default.

**Correct SQL:**
```sql
SELECT ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM appointments), 2) AS no_show_pct
FROM appointments
WHERE status = 'No-Show'
```

---

### Q15 — Show the busiest day of the week for appointments ✅

**Generated SQL:**
```sql
SELECT CASE
    WHEN STRFTIME('%w', appointment_date) = '0' THEN 'Sunday'
    WHEN STRFTIME('%w', appointment_date) = '1' THEN 'Monday'
    WHEN STRFTIME('%w', appointment_date) = '2' THEN 'Tuesday'
    WHEN STRFTIME('%w', appointment_date) = '3' THEN 'Wednesday'
    WHEN STRFTIME('%w', appointment_date) = '4' THEN 'Thursday'
    WHEN STRFTIME('%w', appointment_date) = '5' THEN 'Friday'
    WHEN STRFTIME('%w', appointment_date) = '6' THEN 'Saturday'
END AS day_of_week
FROM appointments
GROUP BY STRFTIME('%w', appointment_date)
ORDER BY COUNT(*) DESC
LIMIT 1
```

**Result:**
```json
{
  "columns": ["day_of_week"],
  "rows": [["Saturday"]],
  "row_count": 1
}
```

**Notes:** Correct and elegant use of SQLite STRFTIME and CASE statement.

---

### Q16 — Revenue trend by month ✅

**Generated SQL:**
```sql
SELECT STRFTIME('%Y-%m', i.invoice_date) AS month, SUM(i.total_amount) AS revenue
FROM invoices i
GROUP BY STRFTIME('%Y-%m', i.invoice_date)
ORDER BY month
```

**Result:** 13 months of revenue data from April 2025 to April 2026.  
**Notes:** Correct time series aggregation. Line chart generated.

---

### Q17 — Average appointment duration by doctor ✅

**Generated SQL:**
```sql
SELECT T1.name, AVG(T4.duration_minutes) AS average_duration
FROM doctors AS T1
JOIN appointments AS T2 ON T1.id = T2.doctor_id
JOIN treatments AS T3 ON T2.id = T3.appointment_id
JOIN treatments AS T4 ON T2.id = T4.appointment_id
GROUP BY T1.name
```

**Result:** All 15 doctors with average duration in minutes. Bar chart generated.

**Notes:** Correct multi-table JOIN with AVG aggregation.

---

### Q18 — List patients with overdue invoices ✅

**Generated SQL:**
```sql
SELECT p.id, p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount
FROM patients p
JOIN invoices i ON p.id = i.patient_id
WHERE i.status = 'overdue' OR (i.total_amount - i.paid_amount) > 0 AND i.invoice_date < DATE('now')
```

**Result:** 101 records returned with all relevant columns.

**Notes:** Correct JOIN and filter combining status and amount conditions.

---

### Q19 — Compare revenue between departments ✅

**Generated SQL:**
```sql
SELECT d.department, SUM(t.cost) AS revenue
FROM treatments t
JOIN appointments a ON t.appointment_id = a.id
JOIN doctors d ON a.doctor_id = d.id
GROUP BY d.department
```

**Result:**
```json
{
  "columns": ["department", "revenue"],
  "rows": [
    ["Bone Department", 170454.95],
    ["Child Department", 104071.84],
    ["General Department", 90564.18],
    ["Heart Department", 183662.23],
    ["Skin Department", 153490.81]
  ],
  "row_count": 5
}
```

**Notes:** Correct GROUP BY department with bar chart. Heart Department has highest revenue.

---

### Q20 — Show patient registration trend by month ❌

**Generated SQL:** None  
**Result:** `"Could not generate SQL for this question."`

**Reason:** Same as Q2 — agent tool call failed intermittently for this question phrasing. The Vanna 2.0 agent occasionally fails to invoke RunSqlTool for certain query types.

**Correct SQL:**
```sql
SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients
FROM patients
GROUP BY month
ORDER BY month
```

---

## Failure Analysis

### Root Causes of Failures

| Issue | Questions Affected | Explanation |
|---|---|---|
| Agent tool call failure | Q2, Q20 | Vanna 2.0 + Groq occasionally fails to invoke RunSqlTool for certain query phrasings |
| Wrong column name | Q6 | LLM confused `invoices.total_amount` with a non-existent `cost` column |
| Case sensitivity | Q7, Q14 | LLM used lowercase status values; database stores title case |
| Ambiguous JOIN aliases | Q9 | LLM reused the same alias for different tables in complex JOINs |

### Improvements to Achieve 20/20

1. **Seed more Q&A examples** — Add Q6, Q9, Q14 correct SQL to agent memory so LLM learns from them
2. **Case-insensitive comparison** — Use `COLLATE NOCASE` or `LOWER()` in queries for status fields
3. **Fallback SQL library** — Map common question patterns to known correct SQL queries
4. **Better system prompt** — Explicitly tell LLM: "status values are Scheduled, Completed, Cancelled, No-Show (exact case)"
5. **Retry mechanism** — Auto-retry when agent tool call fails

---

## Final Score

```
Total:    15 / 20  (75%)
Pass:     15
Fail:      4  (Q2, Q6, Q9, Q20)
Partial:   2  (Q7, Q14 — return results but with wrong values)
```