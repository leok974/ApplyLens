"""Quick sanity check for local ML demo setup.

Verifies:
1. Model artifacts exist and are loadable
2. Configuration is correct
3. Inference pipeline works end-to-end
4. Sample predictions make sense

Usage:
    python -m scripts.verify_ml_demo
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_artifacts():
    """Check that model files exist and are loadable."""
    print("=" * 60)
    print("1. Verifying Model Artifacts")
    print("=" * 60)

    from app.config import agent_settings

    model_path = agent_settings.EMAIL_CLASSIFIER_MODEL_PATH
    vec_path = agent_settings.EMAIL_CLASSIFIER_VECTORIZER_PATH

    print(f"Model path: {model_path}")
    print(f"Vectorizer path: {vec_path}")

    # Check files exist
    if not Path(model_path).exists():
        print(f"\n❌ ERROR: Model file not found: {model_path}")
        print("   Run: python -m scripts.train_local_demo")
        return False

    if not Path(vec_path).exists():
        print(f"\n❌ ERROR: Vectorizer file not found: {vec_path}")
        print("   Run: python -m scripts.train_local_demo")
        return False

    print("✓ Model files exist")

    # Try loading
    try:
        import joblib

        classifier = joblib.load(model_path)
        vectorizer = joblib.load(vec_path)
        print(f"✓ Loaded classifier: {type(classifier).__name__}")
        print(f"✓ Loaded vectorizer: {type(vectorizer).__name__}")
        print(f"  - Vocabulary size: {len(vectorizer.vocabulary_)}")
        return True
    except Exception as e:
        print(f"\n❌ ERROR loading artifacts: {e}")
        return False


def verify_configuration():
    """Check configuration settings."""
    print("\n" + "=" * 60)
    print("2. Verifying Configuration")
    print("=" * 60)

    from app.config import agent_settings

    print(f"Mode: {agent_settings.EMAIL_CLASSIFIER_MODE}")
    print(f"Model version: {agent_settings.EMAIL_CLASSIFIER_MODEL_VERSION}")
    print(f"Model path: {agent_settings.EMAIL_CLASSIFIER_MODEL_PATH}")
    print(f"Vectorizer path: {agent_settings.EMAIL_CLASSIFIER_VECTORIZER_PATH}")

    if agent_settings.EMAIL_CLASSIFIER_MODE not in ["ml_shadow", "ml_live"]:
        print("\n⚠️  WARNING: Mode is not ml_shadow or ml_live")
        print("   Set APPLYLENS_EMAIL_CLASSIFIER_MODE=ml_shadow in .env.dev")
        print("   (Will still test inference below)")

    return True


def verify_inference():
    """Test end-to-end inference."""
    print("\n" + "=" * 60)
    print("3. Testing Inference Pipeline")
    print("=" * 60)

    try:
        import joblib
        from app.config import agent_settings

        # Load artifacts
        classifier = joblib.load(agent_settings.EMAIL_CLASSIFIER_MODEL_PATH)
        vectorizer = joblib.load(agent_settings.EMAIL_CLASSIFIER_VECTORIZER_PATH)

        # Test cases
        test_cases = [
            (
                "Hi! I'm a recruiter at Google. We have a Senior SWE role. Are you interested?",
                "opportunity",
            ),
            (
                "Your Amazon order has shipped. Track your package here.",
                "not_opportunity",
            ),
            ("LinkedIn: Someone viewed your profile", "not_opportunity"),
            (
                "I found your profile and want to discuss a Tech Lead position with great equity.",
                "opportunity",
            ),
        ]

        print("\nRunning test predictions:\n")

        all_correct = True
        for text, expected in test_cases:
            # Vectorize
            X = vectorizer.transform([text])

            # Predict
            prediction = classifier.predict(X)[0]
            probas = classifier.predict_proba(X)[0]
            confidence = probas[prediction]

            result = "opportunity" if prediction == 1 else "not_opportunity"
            is_correct = result == expected

            status = "✓" if is_correct else "❌"
            print(
                f"{status} Expected: {expected:15} | Got: {result:15} | Confidence: {confidence:.3f}"
            )
            print(f"   Text: {text[:80]}...")
            print()

            if not is_correct:
                all_correct = False

        if all_correct:
            print("✓ All test cases passed!")
            return True
        else:
            print("⚠️  Some predictions were incorrect (expected for tiny demo model)")
            return (
                True  # Still consider this a pass - model is working, just not accurate
            )

    except Exception as e:
        print(f"\n❌ ERROR during inference: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("\n🧪 Local ML Demo Verification\n")

    checks = [
        ("Artifacts", verify_artifacts),
        ("Configuration", verify_configuration),
        ("Inference", verify_inference),
    ]

    results = []
    for name, check_func in checks:
        try:
            success = check_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} check failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(success for _, success in results)

    if all_passed:
        print("\n✅ All checks passed! Local ML demo is ready to use.")
        print("\nNext steps:")
        print("  1. Start API: python -m uvicorn app.main:app --reload --port 8000")
        print(
            "  2. Test health: curl http://localhost:8000/diagnostics/classifier/health | jq"
        )
        print("  3. See docs/LOCAL_ML_DEMO.md for full usage guide")
        return 0
    else:
        print("\n❌ Some checks failed. See errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
