import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "clinic.db"

def random_date(start_days_ago, end_days_ago=0):
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")

def random_datetime(start_days_ago, end_days_ago=0):
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    delta = end - start
    dt = start + timedelta(
        days=random.randint(0, delta.days),
        hours=random.randint(8, 17),
        minutes=random.choice([0, 15, 30, 45])
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop tables if exist
    cursor.executescript("""
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS treatments;
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS patients;
    """)

    # Create tables
    cursor.executescript("""
        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT,
            city TEXT,
            registered_date DATE
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            department TEXT,
            phone TEXT
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATETIME,
            status TEXT,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            treatment_name TEXT,
            cost REAL,
            duration_minutes INTEGER,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        );

        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            invoice_date DATE,
            total_amount REAL,
            paid_amount REAL,
            status TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
    """)

    # Insert doctors
    specializations = [
        ("Dermatology", "Skin Department"),
        ("Cardiology", "Heart Department"),
        ("Orthopedics", "Bone Department"),
        ("General", "General Department"),
        ("Pediatrics", "Child Department"),
    ]
    doctor_names = [
        "Dr. James Wilson", "Dr. Sarah Connor", "Dr. Michael Brown",
        "Dr. Emily Davis", "Dr. Robert Taylor", "Dr. Lisa Anderson",
        "Dr. David Martinez", "Dr. Jennifer Thomas", "Dr. Charles Jackson",
        "Dr. Patricia White", "Dr. Mark Harris", "Dr. Nancy Lewis",
        "Dr. Steven Clark", "Dr. Karen Walker", "Dr. Paul Hall"
    ]
    doctors = []
    for i, name in enumerate(doctor_names):
        spec, dept = specializations[i % len(specializations)]
        phone = f"555-{random.randint(1000,9999)}" if random.random() > 0.1 else None
        doctors.append((name, spec, dept, phone))
    cursor.executemany(
        "INSERT INTO doctors (name, specialization, department, phone) VALUES (?,?,?,?)",
        doctors
    )

    # Insert patients
    first_names = ["John","Jane","Michael","Emily","Robert","Sarah","David","Lisa",
                   "James","Mary","William","Patricia","Richard","Linda","Thomas",
                   "Barbara","Charles","Susan","Joseph","Jessica","Daniel","Karen",
                   "Matthew","Nancy","Anthony","Betty","Mark","Helen","Donald","Sandra"]
    last_names = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller",
                  "Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez",
                  "Wilson","Anderson","Taylor","Thomas","Moore","Jackson","Martin"]
    cities = ["New York","Los Angeles","Chicago","Houston","Phoenix",
              "Philadelphia","San Antonio","San Diego","Dallas","San Jose"]
    genders = ["M", "F"]

    patients = []
    for i in range(200):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        email = f"{fn.lower()}.{ln.lower()}{i}@email.com" if random.random() > 0.1 else None
        phone = f"555-{random.randint(1000,9999)}" if random.random() > 0.15 else None
        dob = random_date(365*60, 365*18)
        gender = random.choice(genders)
        city = random.choice(cities)
        reg_date = random_date(365)
        patients.append((fn, ln, email, phone, dob, gender, city, reg_date))
    cursor.executemany(
        "INSERT INTO patients (first_name,last_name,email,phone,date_of_birth,gender,city,registered_date) VALUES (?,?,?,?,?,?,?,?)",
        patients
    )

    # Insert appointments (500)
    statuses = ["Scheduled", "Completed", "Cancelled", "No-Show"]
    status_weights = [0.2, 0.55, 0.15, 0.10]
    appointments = []
    # Make some patients repeat visitors
    repeat_patients = random.sample(range(1, 201), 40)

    for i in range(500):
        if random.random() < 0.4 and repeat_patients:
            patient_id = random.choice(repeat_patients)
        else:
            patient_id = random.randint(1, 200)
        # Make some doctors busier
        doctor_id = random.choices(range(1, 16), weights=[10,8,8,6,6,5,5,5,4,4,3,3,3,3,3])[0]
        appt_date = random_datetime(365)
        status = random.choices(statuses, weights=status_weights)[0]
        notes = f"Patient notes {i}" if random.random() > 0.4 else None
        appointments.append((patient_id, doctor_id, appt_date, status, notes))
    cursor.executemany(
        "INSERT INTO appointments (patient_id,doctor_id,appointment_date,status,notes) VALUES (?,?,?,?,?)",
        appointments
    )

    # Insert treatments (350) - only for completed appointments
    cursor.execute("SELECT id FROM appointments WHERE status='Completed'")
    completed_ids = [row[0] for row in cursor.fetchall()]
    treatment_names = ["Blood Test","X-Ray","ECG","MRI Scan","Ultrasound",
                       "Consultation","Surgery","Vaccination","Physiotherapy","Biopsy"]
    treatments = []
    selected = random.sample(completed_ids, min(350, len(completed_ids)))
    for appt_id in selected:
        treatment = random.choice(treatment_names)
        cost = round(random.uniform(50, 5000), 2)
        duration = random.choice([15, 30, 45, 60, 90, 120])
        treatments.append((appt_id, treatment, cost, duration))
    cursor.executemany(
        "INSERT INTO treatments (appointment_id,treatment_name,cost,duration_minutes) VALUES (?,?,?,?)",
        treatments
    )

    # Insert invoices (300)
    invoice_statuses = ["Paid", "Pending", "Overdue"]
    invoice_weights = [0.6, 0.25, 0.15]
    invoices = []
    patient_ids = random.choices(range(1, 201), k=300)
    for pid in patient_ids:
        inv_date = random_date(365)
        total = round(random.uniform(100, 5000), 2)
        status = random.choices(invoice_statuses, weights=invoice_weights)[0]
        paid = total if status == "Paid" else round(random.uniform(0, total * 0.5), 2)
        invoices.append((pid, inv_date, total, paid, status))
    cursor.executemany(
        "INSERT INTO invoices (patient_id,invoice_date,total_amount,paid_amount,status) VALUES (?,?,?,?,?)",
        invoices
    )

    conn.commit()

    # Print summary
    cursor.execute("SELECT COUNT(*) FROM patients")
    p = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM doctors")
    d = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM appointments")
    a = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM treatments")
    t = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM invoices")
    i = cursor.fetchone()[0]

    print(f"Created {p} patients, {d} doctors, {a} appointments, {t} treatments, {i} invoices")
    conn.close()

if __name__ == "__main__":
    setup_database()