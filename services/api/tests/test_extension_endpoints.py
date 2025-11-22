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
