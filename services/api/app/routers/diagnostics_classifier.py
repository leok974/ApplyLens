"""
Diagnostic endpoints for email classifier health checks.

Provides visibility into classifier state, model versions, and basic sanity checks.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.deps import optional_current_user
from app.models import Email
from app.services.classification import get_global_classifier, reload_classifier

router = APIRouter(prefix="/diagnostics/classifier", tags=["diagnostics"])


class ClassifierHealthResponse(BaseModel):
    """Health check response for email classifier."""

    ok: bool  # Overall health status
    status: str  # "healthy" | "degraded" | "unhealthy"
    mode: str  # "heuristic" | "ml_shadow" | "ml_live" | "unknown"
    model_version: str
    has_model_artifacts: bool  # Whether ML model files are loaded
    uses_ml: bool  # Whether classifier is configured to use ML
    ml_model_loaded: bool  # Deprecated: use has_model_artifacts
    vectorizer_loaded: bool  # Deprecated: use has_model_artifacts
    message: str  # Human-readable status message
    sample_prediction: dict | None = None
    error: str | None = None


@router.get("/health", response_model=ClassifierHealthResponse)
def classifier_health_check(current_user=Depends(optional_current_user)):
    """
    Check email classifier health and configuration.

    Returns:
        - Classifier mode and model version
        - Whether ML models are loaded
        - Test classification on a synthetic email
        - Overall health status with message
    """
    try:
        classifier = get_global_classifier()

        # Check if ML models are loaded
        ml_loaded = classifier.ml_model is not None
        vec_loaded = classifier.vectorizer is not None
        has_artifacts = ml_loaded and vec_loaded

        # Determine if classifier is configured to use ML
        uses_ml = classifier.mode in ("ml_shadow", "ml_live")

        # Test classification on a synthetic email
        test_email = Email(
            subject="Interview invitation for Senior Engineer role at Acme Corp",
            body_text="We'd like to schedule a phone screen with you next week...",
            sender="recruiter@acme-corp.com",
            thread_id="test-thread",
        )

        result = classifier.classify(test_email)

        # Determine health status
        if uses_ml and not has_artifacts:
            status = "degraded"
            ok = False
            message = (
                f"Classifier mode is {classifier.mode} but ML artifacts are not loaded"
            )
        elif uses_ml and has_artifacts:
            status = "healthy"
            ok = True
            message = (
                f"Classifier running in {classifier.mode} mode with ML model loaded"
            )
        else:
            status = "healthy"
            ok = True
            message = f"Classifier running in {classifier.mode} mode (heuristic-only)"

        return ClassifierHealthResponse(
            ok=ok,
            status=status,
            mode=classifier.mode,
            model_version=classifier.model_version,
            has_model_artifacts=has_artifacts,
            uses_ml=uses_ml,
            ml_model_loaded=ml_loaded,  # Deprecated but kept for compatibility
            vectorizer_loaded=vec_loaded,  # Deprecated but kept for compatibility
            message=message,
            sample_prediction={
                "category": result.category,
                "is_real_opportunity": result.is_real_opportunity,
                "confidence": result.confidence,
                "source": result.source,
            },
        )

    except Exception as e:
        return ClassifierHealthResponse(
            ok=False,
            status="unhealthy",
            mode="unknown",
            model_version="unknown",
            has_model_artifacts=False,
            uses_ml=False,
            ml_model_loaded=False,
            vectorizer_loaded=False,
            message="Classifier initialization failed",
            error=str(e),
        )


@router.post("/reload")
def reload_classifier_endpoint(current_user=Depends(optional_current_user)):
    """
    Reload the global classifier (e.g., after deploying new model).

    This allows hot-swapping models without restarting the server.
    """
    try:
        reload_classifier()
        new_classifier = get_global_classifier()

        return {
            "status": "reloaded",
            "mode": new_classifier.mode,
            "model_version": new_classifier.model_version,
            "ml_model_loaded": new_classifier.ml_model is not None,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
