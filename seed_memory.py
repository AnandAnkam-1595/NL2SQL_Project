import asyncio
import uuid
from vanna_setup import agent, memory
from vanna.core.tool import ToolContext
from vanna.core.user.models import User

# Create a user context for seeding
seed_user = User(id="admin", email="admin@example.com", group_memberships=["admin", "user"])

# Provide all required ToolContext fields
ctx = ToolContext(
    user=seed_user,
    conversation_id=str(uuid.uuid4()),
    request_id=str(uuid.uuid4()),
    agent_memory=memory
)

examples = [
    ("How many patients?", "SELECT COUNT(*) FROM patients"),
    ("List doctors", "SELECT name, specialization FROM doctors"),
    ("Appointments last month", "SELECT * FROM appointments WHERE appointment_date >= date('now','-30 days')"),
    ("Top patients", "SELECT patient_id, SUM(total_amount) FROM invoices GROUP BY patient_id ORDER BY SUM(total_amount) DESC LIMIT 5"),
    ("Revenue", "SELECT SUM(total_amount) FROM invoices"),
    ("Revenue by doctor", """SELECT d.name, SUM(i.total_amount)
FROM doctors d
JOIN appointments a ON d.id = a.doctor_id
JOIN invoices i ON a.patient_id = i.patient_id
GROUP BY d.name"""),
    ("Cancelled appointments", "SELECT COUNT(*) FROM appointments WHERE status='Cancelled'"),
    ("City patients", "SELECT city, COUNT(*) FROM patients GROUP BY city"),
    ("Unpaid invoices", "SELECT * FROM invoices WHERE status='Pending'"),
    ("No show percentage", """SELECT (COUNT(*)*100.0)/(SELECT COUNT(*) FROM appointments)
FROM appointments WHERE status='No-Show'"""),
    ("Busiest doctor", "SELECT doctor_id, COUNT(*) FROM appointments GROUP BY doctor_id ORDER BY COUNT(*) DESC LIMIT 1"),
    ("Monthly revenue", "SELECT strftime('%Y-%m', invoice_date), SUM(total_amount) FROM invoices GROUP BY 1"),
    ("Frequent patients", "SELECT patient_id, COUNT(*) FROM appointments GROUP BY patient_id HAVING COUNT(*)>3"),
    ("Overdue invoices", "SELECT * FROM invoices WHERE status='Pending'"),
    ("Appointments count", "SELECT COUNT(*) FROM appointments")
]

async def seed():
    for q, sql in examples:
        await memory.save_tool_usage(
            question=q,
            tool_name="RunSqlTool",
            args={"sql": sql},
            context=ctx,
            success=True
        )
        print(f"  Seeded: {q}")
    print("\n Memory seeded successfully!")

asyncio.run(seed())