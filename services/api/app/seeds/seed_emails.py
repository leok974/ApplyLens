from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Email
from ..es import ensure_index, es, ES_ENABLED, INDEX


def run():
    ensure_index()
    db: Session = SessionLocal()
    samples = [
        Email(thread_id="t1", from_addr="recruiter@company.com", to_addr="you@example.com",
              subject="Interview Invitation – Backend Engineer", body_text="Hi, I'm a recruiter at TechCorp. We would like to invite you for an interview for our Backend Engineer position.", label="interview"),
        Email(thread_id="t2", from_addr="no-reply@greenhouse.io", to_addr="you@example.com",
              subject="Application received – ML Engineer", body_text="Thank you for applying to the ML Engineer position at our company. We'll review your application soon.", label="application_receipt"),
        Email(thread_id="t3", from_addr="newsletter@jobsweekly.com", to_addr="you@example.com",
              subject="Top roles this week", body_text="Check out the hottest job opportunities this week in tech.", label="newsletter"),
        Email(thread_id="t4", from_addr="talent@startup.io", to_addr="you@example.com",
              subject="Exciting opportunity", body_text="Our talent partner team found your profile interesting. We have a great role open for a senior engineer.", label="job_opportunity"),
    ]
    for s in samples:
        db.add(s)
    db.commit()

    # Re-query to get IDs and index into Elasticsearch
    rows = db.query(Email).all()
    if ES_ENABLED and es is not None:
        for r in rows:
            doc = {
                "id": r.id,
                "thread_id": r.thread_id,
                "from_addr": r.from_addr,
                "subject": r.subject,
                "subject_shingles": r.subject,
                "subject_suggest": r.subject,
                "body_text": r.body_text,
                "body_shingles": r.body_text,
                "body_sayt": r.body_text,
                "label": r.label,
                "received_at": r.received_at.isoformat() if r.received_at else None,
            }
            es.index(index=INDEX, id=r.id, document=doc)
    db.close()
    print(f"Seeded {len(samples)} emails into database and Elasticsearch")

if __name__ == "__main__":
    run()
