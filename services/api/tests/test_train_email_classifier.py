# services/api/tests/test_train_email_classifier.py


import numpy as np


def test_train_email_classifier_main_creates_artifacts(tmp_path, monkeypatch, capsys):
    """
    Integration-ish test for scripts/train_email_classifier.py

    - Monkeypatches load_training_data to avoid using the real DB.
    - Redirects MODEL_DIR/MODEL_PATH/VEC_PATH to tmp_path.
    - Calls main(), ensuring:
        * The script runs without error
        * Model + vectorizer artifacts are created
        * The saved model can be loaded and used to predict
    """
    # Import inside test so pytest can monkeypatch before module-level code runs if needed.
    import scripts.train_email_classifier as te

    # --- Redirect model paths to tmp_path ---
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "email_opp_model.joblib"
    vec_path = model_dir / "email_opp_vectorizer.joblib"

    # Override the module constants (now DEFAULT_MODEL_PATH and DEFAULT_VEC_PATH)
    monkeypatch.setattr(te, "MODEL_DIR", str(model_dir))
    monkeypatch.setattr(te, "DEFAULT_MODEL_PATH", str(model_path))
    monkeypatch.setattr(te, "DEFAULT_VEC_PATH", str(vec_path))

    # --- Fake DB training data ---
    def fake_load_training_data(_db, min_confidence=0.8):
        # Synthetic tiny dataset with enough samples for stratified split (need at least 4 per class)
        texts = [
            "Weekly newsletter from SomeCompany — our latest news",  # non-opp
            "Your interview with Acme Corp — confirmation",  # opp
            "Thanks for your application — HR screening stage",  # opp
            "Your receipt from Online Store",  # non-opp
            "Check out our latest blog post about AI trends",  # non-opp
            "Phone screen scheduled for next Tuesday",  # opp
            "Your order #12345 has shipped",  # non-opp
            "We'd like to discuss the Senior Engineer role",  # opp
            "Monthly digest from TechNews",  # non-opp
            "Offer letter attached for your review",  # opp
        ]
        labels = [
            0,  # not opportunity
            1,  # opportunity
            1,
            0,
            0,  # not opportunity
            1,  # opportunity
            0,
            1,
            0,  # not opportunity
            1,  # opportunity
        ]
        return texts, labels

    monkeypatch.setattr(te, "load_training_data", fake_load_training_data)

    # --- Fake SessionLocal so we don't need a real DB ---
    class DummySession:
        def close(self):
            pass

    monkeypatch.setattr(te, "SessionLocal", lambda: DummySession())

    # --- Run the training script main() ---
    te.main()

    # Ensure it printed validation results (sanity check, not strict)
    out = capsys.readouterr().out
    assert "=== Validation Results ===" in out or "Training complete" in out

    # --- Check that artifacts were written ---
    assert model_path.exists(), "Model file was not created"
    assert vec_path.exists(), "Vectorizer file was not created"

    # --- Load and do a tiny smoke prediction ---
    import joblib

    clf = joblib.load(model_path)
    vec = joblib.load(vec_path)

    sample_texts = [
        "Interview scheduled with Foo Inc.",
        "This is your weekly discount newsletter from Bargain Corp.",
    ]
    X = vec.transform(sample_texts)
    proba = clf.predict_proba(X)[:, 1]

    # We don't assert exact numbers, just that probabilities are in [0, 1]
    assert proba.shape == (2,)
    assert np.all(proba >= 0.0) and np.all(proba <= 1.0)
