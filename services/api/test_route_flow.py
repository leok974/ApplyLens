from app.db import get_db
from app.models import Email, Application
from sqlalchemy import text, func

db = next(get_db())
try:
    # Test the exact query from list_opportunities
    cutoff = func.now() - text("INTERVAL '6 months'")
    result = (
        db.query(Email, Application)
        .outerjoin(Application, Application.email_id == Email.id)
        .filter(Email.owner_email == "leoklemet.pa@gmail.com")
        .filter(Email.received_at >= cutoff)
        .all()
    )
    print(f"Query returned {len(result)} results")

    # Try to build response for first item
    if result:
        email, application = result[0]
        print(
            f"First email: id={email.id}, subject={email.subject[:50] if email.subject else None}"
        )

        # Try OpportunityResponse construction
        from app.routers.opportunities import OpportunityResponse
        from app.business.priority import compute_opportunity_priority

        priority = compute_opportunity_priority(
            application_status=application.status.value
            if application and application.status
            else None,
            email_category=email.category,
            last_message_at=email.received_at,
        )

        response = OpportunityResponse(
            id=email.id,
            owner_email=email.owner_email or "leoklemet.pa@gmail.com",
            source=email.source or (application.source if application else "email"),
            title=email.subject or "",
            company=email.company or "Unknown",
            location=application.location if application else None,
            remote_flag=application.remote_flag if application else None,
            salary_text=application.salary_text if application else None,
            level=application.level if application else None,
            tech_stack=application.tech_stack if application else None,
            apply_url=application.apply_url if application else None,
            posted_at=application.posted_at if application else None,
            created_at=email.received_at,
            match_bucket=application.match_bucket if application else None,
            match_score=application.match_score if application else None,
            priority=priority,
        )
        print(f"OpportunityResponse created: {response.id}")

        # Try model_dump (what FastAPI does)
        data = response.model_dump()
        print(f"model_dump successful, keys: {list(data.keys())[:5]}")

        # Try JSON serialization
        import json

        json_str = json.dumps(data, default=str)
        print(f"JSON successful, length: {len(json_str)}")
        print("=" * 60)
        print("ALL TESTS PASSED - No issue found in code path")
        print("=" * 60)

except Exception as e:
    import traceback

    print(f"ERROR FOUND: {e}")
    print("=" * 60)
    traceback.print_exc()
