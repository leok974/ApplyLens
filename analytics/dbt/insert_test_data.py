from google.cloud import bigquery
import os
from datetime import datetime, timedelta

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    r"D:\ApplyLens\analytics\dbt\applylens-ci.json"
)
client = bigquery.Client(project="applylens-gmail-1759983601")

# Insert sample email data
print("📧 Inserting sample email data...")
rows_to_insert = []
for i in range(60):  # 60 days of data
    dt = datetime.now() - timedelta(days=i)
    rows_to_insert.append(
        {
            "id": f"email_{i}",
            "received_at": dt.isoformat(),
            "created_at": dt.isoformat(),
            "updated_at": dt.isoformat(),
            "sender": f"recruiter{i % 5}@company{i % 10}.com",
            "subject": f"Job Opportunity #{i}",
            "risk_score": 0.3 + (i % 10) * 0.07,
            "category": ["recruiter", "interview", "offer", "rejection"][i % 4],
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "features_json": "{}",
        }
    )

errors = client.insert_rows_json("applylens.public_emails", rows_to_insert)
if errors:
    print(f"❌ Errors: {errors}")
else:
    print(f"✅ Inserted {len(rows_to_insert)} email records")

# Insert sample application data
print("\n📄 Inserting sample application data...")
app_rows = []
for i in range(30):  # 30 applications
    dt = datetime.now() - timedelta(days=i * 2)
    app_rows.append(
        {
            "id": f"app_{i}",
            "created_at": dt.isoformat(),
            "updated_at": (datetime.now() - timedelta(days=i)).isoformat(),
            "company": f"Company {i % 5}",
            "role": ["Software Engineer", "Senior Engineer", "Tech Lead", "Manager"][
                i % 4
            ],
            "status": ["applied", "interviewing", "offered", "rejected"][i % 4],
            "applied_date": dt.date().isoformat(),
        }
    )

errors = client.insert_rows_json("applylens.public_applications", app_rows)
if errors:
    print(f"❌ Errors: {errors}")
else:
    print(f"✅ Inserted {len(app_rows)} application records")

print("\n🎉 Test data ready!")
