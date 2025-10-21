"""reCAPTCHA verification for anti-bot protection.

Integrates Google reCAPTCHA v3 to protect demo login from abuse.
"""
import logging
import httpx
from app.config import agent_settings
from app.core.metrics import recaptcha_verify_total, recaptcha_score

logger = logging.getLogger(__name__)

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


async def verify_captcha(token: str, remoteip: str | None = None) -> bool:
    """Verify reCAPTCHA token with Google.
    
    Args:
        token: reCAPTCHA response token from frontend
        remoteip: Optional client IP for verification
        
    Returns:
        True if verification passed, False otherwise
    """
    if not agent_settings.RECAPTCHA_ENABLED:
        logger.debug("reCAPTCHA disabled - skipping verification")
        recaptcha_verify_total.labels(status="disabled").inc()
        return True
    
    if not token:
        logger.warning("reCAPTCHA verification failed: Missing token")
        recaptcha_verify_total.labels(status="failure").inc()
        return False
    
    if not agent_settings.RECAPTCHA_SECRET_KEY:
        logger.error("reCAPTCHA enabled but SECRET_KEY not configured")
        recaptcha_verify_total.labels(status="failure").inc()
        return False
    
    # Build verification request
    data = {
        "secret": agent_settings.RECAPTCHA_SECRET_KEY,
        "response": token,
    }
    
    if remoteip:
        data["remoteip"] = remoteip
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(VERIFY_URL, data=data)
            response.raise_for_status()
            result = response.json()
            
            success = bool(result.get("success"))
            score = float(result.get("score", 1.0))
            action = result.get("action", "unknown")
            
            # Track score histogram
            recaptcha_score.observe(score)
            
            if not success:
                error_codes = result.get("error-codes", [])
                logger.warning(f"reCAPTCHA verification failed: {error_codes}")
                recaptcha_verify_total.labels(status="failure").inc()
                return False
            
            if score < agent_settings.RECAPTCHA_MIN_SCORE:
                logger.warning(
                    f"reCAPTCHA score too low: {score} < {agent_settings.RECAPTCHA_MIN_SCORE} "
                    f"(action={action})"
                )
                recaptcha_verify_total.labels(status="low_score").inc()
                return False
            
            logger.info(f"reCAPTCHA verified: score={score}, action={action}")
            recaptcha_verify_total.labels(status="success").inc()
            return True
            
    except httpx.HTTPError as e:
        logger.error(f"reCAPTCHA verification request failed: {e}")
        recaptcha_verify_total.labels(status="failure").inc()
        return False
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {e}")
        recaptcha_verify_total.labels(status="failure").inc()
        return False
