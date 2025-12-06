import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profile_me_ok():
    r = client.get("/api/profile/me")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert isinstance(data.get("projects", []), list)


def test_generate_form_answers_ok():
    payload = {
        "job": {
            "title": "AI Engineer",
            "company": "Acme",
            "url": "https://jobs.acme.ai",
        },
        "fields": [
            {
                "field_id": "cover_letter",
                "label": "Why do you want to work here?",
                "type": "textarea",
            },
            {
                "field_id": "project_example",
                "label": "Describe a recent project you're proud of",
                "type": "textarea",
            },
        ],
    }
    r = client.post("/api/extension/generate-form-answers", json=payload)
    assert r.status_code == 200
    data = r.json()

    # Response structure: {job: {...}, answers: [{field_id, answer}, ...]}
    assert "job" in data
    assert "answers" in data
    answers = data["answers"]
    assert len(answers) >= 2
    assert any(a["field_id"] == "cover_letter" for a in answers)
    assert any(a["field_id"] == "project_example" for a in answers)

    # Check that answers have text
    for ans in answers:
        assert "answer" in ans
        assert len(ans["answer"]) > 0


@pytest.mark.smoke
def test_companion_pipeline_smoke():
    """
    End-to-end smoke test for the Companion pipeline.

    Validates the core contract the extension depends on:
    - Profile endpoint is reachable (used for "Signed in as...")
    - Generate-form-answers returns at least one non-empty answer
    - Response follows expected schema

    This is the fast "is the pipeline alive?" check for CI/local testing.
    """
    # 1) Profile should be reachable (same endpoint extension uses)
    resp_profile = client.get("/api/profile/me")
    assert resp_profile.status_code == 200
    profile = resp_profile.json()
    assert "name" in profile
    assert "headline" in profile

    # 2) Generate form answers for a minimal smoke test job
    payload = {
        "job": {
            "title": "Smoke Test AI Engineer",
            "company": "ApplyLens",
            "url": "https://example.com/jobs/smoke-test",
        },
        "fields": [
            {
                "field_id": "first_name",
                "semantic_key": "first_name",
                "label": "First name",
                "type": "text",
            },
            {
                "field_id": "last_name",
                "semantic_key": "last_name",
                "label": "Last name",
                "type": "text",
            },
            {
                "field_id": "why_interested",
                "semantic_key": "why_interested",
                "label": "Why are you interested in this role?",
                "type": "textarea",
            },
        ],
        "profile_context": {
            "name": profile.get("name"),
            "headline": profile.get("headline"),
            "locations": profile.get("locations", []),
            "target_roles": profile.get("target_roles", []),
            "tech_stack": profile.get("tech_stack", []),
        },
        "style_prefs": {
            "tone": "confident",
            "length": "short",
        },
    }

    resp_gen = client.post("/api/extension/generate-form-answers", json=payload)
    assert resp_gen.status_code == 200

    data = resp_gen.json()
    # Response structure: {job: {...}, answers: [{field_id, answer}, ...]}
    assert "job" in data
    assert "answers" in data
    answers = data["answers"]
    assert len(answers) > 0

    # At least one field should have a non-empty answer
    # (LLM might skip some fields, but should fill something)
    non_empty_answers = [a for a in answers if a.get("answer", "").strip()]
    assert len(non_empty_answers) > 0, "Expected at least one non-empty answer"

    # Verify answer structure
    for ans in non_empty_answers:
        assert "field_id" in ans
        assert "answer" in ans
        assert isinstance(ans["answer"], str)
        assert len(ans["answer"].strip()) > 0
