"""
Gemini LLM Client for hackathon integration.

Provides email classification and entity extraction using Google's Gemini API
with strict timeouts, error handling, fallback to heuristics, and Datadog observability.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import Datadog instrumentation (graceful degradation if not available)
try:
    from app.observability.datadog import instrument_llm_call, log_llm_operation

    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False

    # Mock decorator when Datadog not available
    def instrument_llm_call(task_type: str):
        def decorator(func):
            return func

        return decorator

    def log_llm_operation(*args, **kwargs):
        pass


logger = logging.getLogger(__name__)


@dataclass
class GeminiConfig:
    """Configuration for Gemini client."""

    project_id: str
    model: str = "gemini-1.5-flash"
    timeout_seconds: float = 5.0
    max_retries: int = 2
    temperature: float = 0.3
    max_tokens: int = 500


class GeminiLLMClient:
    """
    Gemini client for LLM operations with observability.

    Features:
    - Email intent classification
    - Job entity extraction
    - Automatic fallback to heuristics on error
    - Metrics emission for Datadog
    """

    def __init__(self, config: GeminiConfig):
        self.config = config
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Vertex AI Gemini client."""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.config.project_id)
            self._client = GenerativeModel(self.config.model)
            logger.info(f"Gemini client initialized: {self.config.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self._client = None

    @instrument_llm_call("classify")
    async def classify_email_intent(
        self,
        subject: str,
        snippet: str,
        sender: str,
    ) -> Dict[str, Any]:
        """
        Classify email intent using Gemini.

        Returns classification with confidence:
        {
            "intent": "job_application" | "interview" | "offer" | "rejection" | "other",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation",
            "model_used": "gemini" | "heuristic",
            "latency_ms": int
        }
        """
        start_time = time.time()

        # Check if client is available
        if not self._client:
            logger.warning("Gemini client not available, using heuristic fallback")
            return self._heuristic_classify(subject, snippet, sender, start_time)

        try:
            # Build prompt
            prompt = f"""You are an email classifier for a job search assistant.

Classify this email into ONE of these intents:
- job_application: Application confirmations, "we received your application"
- interview: Interview invitations or scheduling
- offer: Job offers or offer letters
- rejection: Rejections or "not moving forward"
- other: Anything else

Email details:
Subject: {subject}
From: {sender}
Snippet: {snippet[:200]}

Respond ONLY with valid JSON:
{{
  "intent": "one of the 5 intents above",
  "confidence": 0.95,
  "reasoning": "Brief 1-sentence explanation"
}}"""

            # Call Gemini with timeout
            response = await asyncio.wait_for(
                self._call_gemini(prompt), timeout=self.config.timeout_seconds
            )

            # Parse response
            result = self._parse_classification(response)
            result["model_used"] = "gemini"
            result["latency_ms"] = int((time.time() - start_time) * 1000)

            return result

        except asyncio.TimeoutError:
            logger.warning(f"Gemini timeout after {self.config.timeout_seconds}s")
            return self._heuristic_classify(subject, snippet, sender, start_time)
        except Exception as e:
            logger.error(f"Gemini classification error: {e}", exc_info=True)
            return self._heuristic_classify(subject, snippet, sender, start_time)

    @instrument_llm_call("extract")
    async def extract_job_entities(
        self,
        subject: str,
        body_snippet: str,
    ) -> Dict[str, Any]:
        """
        Extract job-related entities from email.

        Returns:
        {
            "company": str | null,
            "role": str | null,
            "recruiter_name": str | null,
            "interview_date": str | null,
            "salary_mentioned": bool,
            "model_used": "gemini" | "heuristic",
            "latency_ms": int
        }
        """
        start_time = time.time()

        if not self._client:
            logger.warning("Gemini client not available, using heuristic extraction")
            return self._heuristic_extract(subject, body_snippet, start_time)

        try:
            prompt = f"""You are extracting job-related entities from emails.

Extract these fields from the email (return null if not found):
- company: Company name
- role: Job title/position
- recruiter_name: Person's name (first + last)
- interview_date: Any mentioned interview date (ISO format if possible)
- salary_mentioned: true/false if salary/compensation is mentioned

Email:
Subject: {subject}
Body: {body_snippet[:300]}

Respond ONLY with valid JSON:
{{
  "company": "Company Name" or null,
  "role": "Job Title" or null,
  "recruiter_name": "First Last" or null,
  "interview_date": "2025-01-15" or null,
  "salary_mentioned": true or false
}}"""

            response = await asyncio.wait_for(
                self._call_gemini(prompt), timeout=self.config.timeout_seconds
            )

            result = self._parse_extraction(response)
            result["model_used"] = "gemini"
            result["latency_ms"] = int((time.time() - start_time) * 1000)

            return result

        except asyncio.TimeoutError:
            logger.warning(f"Gemini timeout after {self.config.timeout_seconds}s")
            return self._heuristic_extract(subject, body_snippet, start_time)
        except Exception as e:
            logger.error(f"Gemini extraction error: {e}", exc_info=True)
            return self._heuristic_extract(subject, body_snippet, start_time)

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API and return response text."""
        response = await asyncio.to_thread(
            self._client.generate_content,
            prompt,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            },
        )
        return response.text

    def _parse_classification(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini classification response."""
        try:
            # Try to parse JSON from response
            data = json.loads(response_text)

            # Validate required fields
            if "intent" not in data:
                raise ValueError("Missing 'intent' field")

            return {
                "intent": data.get("intent", "other"),
                "confidence": float(data.get("confidence", 0.5)),
                "reasoning": data.get("reasoning", ""),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            # Return low-confidence default
            return {
                "intent": "other",
                "confidence": 0.3,
                "reasoning": "Failed to parse model response",
            }

    def _parse_extraction(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini extraction response."""
        try:
            data = json.loads(response_text)
            return {
                "company": data.get("company"),
                "role": data.get("role"),
                "recruiter_name": data.get("recruiter_name"),
                "interview_date": data.get("interview_date"),
                "salary_mentioned": bool(data.get("salary_mentioned", False)),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Gemini extraction: {e}")
            return {
                "company": None,
                "role": None,
                "recruiter_name": None,
                "interview_date": None,
                "salary_mentioned": False,
            }

    def _heuristic_classify(
        self, subject: str, snippet: str, sender: str, start_time: float
    ) -> Dict[str, Any]:
        """Fallback heuristic classification."""
        text = f"{subject} {snippet}".lower()

        # Simple keyword matching
        if any(kw in text for kw in ["interview", "schedule", "meet", "call"]):
            intent = "interview"
            confidence = 0.7
        elif any(kw in text for kw in ["offer", "congratulations", "pleased to offer"]):
            intent = "offer"
            confidence = 0.75
        elif any(
            kw in text for kw in ["unfortunately", "not moving forward", "regret"]
        ):
            intent = "rejection"
            confidence = 0.7
        elif any(
            kw in text for kw in ["received your application", "thank you for applying"]
        ):
            intent = "job_application"
            confidence = 0.65
        else:
            intent = "other"
            confidence = 0.5

        return {
            "intent": intent,
            "confidence": confidence,
            "reasoning": "Heuristic keyword matching",
            "model_used": "heuristic",
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    def _heuristic_extract(
        self, subject: str, body_snippet: str, start_time: float
    ) -> Dict[str, Any]:
        """Fallback heuristic entity extraction."""
        text = f"{subject} {body_snippet}"

        # Very basic extraction (can be improved)
        salary_mentioned = any(
            kw in text.lower() for kw in ["$", "salary", "compensation", "k/year"]
        )

        return {
            "company": None,  # Would need NER for reliable extraction
            "role": None,
            "recruiter_name": None,
            "interview_date": None,
            "salary_mentioned": salary_mentioned,
            "model_used": "heuristic",
            "latency_ms": int((time.time() - start_time) * 1000),
        }


# Global client instance (initialized on first use)
_gemini_client: Optional[GeminiLLMClient] = None


def get_gemini_client() -> Optional[GeminiLLMClient]:
    """Get or create Gemini client instance."""
    global _gemini_client

    if _gemini_client is None:
        import os

        # Check if Gemini is enabled
        if not os.getenv("USE_GEMINI_FOR_CLASSIFY") and not os.getenv(
            "USE_GEMINI_FOR_EXTRACT"
        ):
            logger.info("Gemini not enabled (USE_GEMINI_FOR_* flags not set)")
            return None

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set, Gemini unavailable")
            return None

        config = GeminiConfig(
            project_id=project_id,
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "5.0")),
        )

        _gemini_client = GeminiLLMClient(config)

    return _gemini_client
