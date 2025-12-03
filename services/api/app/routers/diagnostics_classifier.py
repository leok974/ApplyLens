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

    status: str  # "healthy" | "degraded" | "unhealthy"
    mode: str  # "heuristic" | "ml_shadow" | "ml_live"
    model_version: str
    ml_model_loaded: bool
    vectorizer_loaded: bool
    test_classification: dict | None = None
    error: str | None = None


@router.get("/health", response_model=ClassifierHealthResponse)
def classifier_health_check(current_user=Depends(optional_current_user)):
    """
    Check email classifier health and configuration.

    Returns:
        - Classifier mode and model version
        - Whether ML models are loaded
        - Test classification on a synthetic email
    """
    try:
        classifier = get_global_classifier()

        # Basic info
        ml_loaded = classifier.ml_model is not None
        vec_loaded = classifier.vectorizer is not None

        # Test classification on a synthetic email
        test_email = Email(
            subject="Interview invitation for Senior Engineer role at Acme Corp",
            snippet="We'd like to schedule a phone screen with you next week...",
            from_address="recruiter@acme-corp.com",
            thread_id="test-thread",
        )

        result = classifier.classify(test_email)

        return ClassifierHealthResponse(
            status="healthy",
            mode=classifier.mode,
            model_version=classifier.model_version,
            ml_model_loaded=ml_loaded,
            vectorizer_loaded=vec_loaded,
            test_classification={
                "category": result.category,
                "is_real_opportunity": result.is_real_opportunity,
                "confidence": result.confidence,
                "source": result.source,
            },
        )

    except Exception as e:
        return ClassifierHealthResponse(
            status="unhealthy",
            mode="unknown",
            model_version="unknown",
            ml_model_loaded=False,
            vectorizer_loaded=False,
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
