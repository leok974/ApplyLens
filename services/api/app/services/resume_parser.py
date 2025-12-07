"""Resume parsing service for text extraction and structured data extraction.

Supports PDF, DOCX, and plain text formats.
Uses LLM for intelligent parsing of resume structure.
"""

import io
import json
import logging
import os
import re
from typing import List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def extract_text_from_resume(filename: str, content: bytes) -> str:
    """Extract text from resume file (PDF, DOCX, or plain text).

    Args:
        filename: Original filename with extension
        content: File content as bytes

    Returns:
        Extracted text content

    Raises:
        ValueError: If file format is not supported
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return _extract_from_pdf(content)
    elif filename_lower.endswith(".docx"):
        return _extract_from_docx(content)
    elif filename_lower.endswith(".txt"):
        return content.decode("utf-8")
    else:
        raise ValueError(
            f"Unsupported file format: {filename}. Supported formats: PDF, DOCX, TXT"
        )


def _extract_from_pdf(content: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError as e:
        logger.error(f"PyPDF2 not available: {e}")
        raise ImportError(
            "PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2==3.0.1"
        )

    try:
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)

        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        result = "\n\n".join(text_parts)
        if not result.strip():
            raise ValueError("PDF appears to be empty or text could not be extracted")
        return result
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def _extract_from_docx(content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError as e:
        logger.error(f"python-docx not available: {e}")
        raise ImportError(
            "python-docx is required for DOCX extraction. Install with: pip install python-docx==1.1.0"
        )

    try:
        docx_file = io.BytesIO(content)
        doc = Document(docx_file)

        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        result = "\n".join(text_parts)
        if not result.strip():
            raise ValueError("DOCX appears to be empty or text could not be extracted")
        return result
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")


# ===== LLM-Powered Profile Extraction =====


class ExtractedProfile(BaseModel):
    """Structured profile data extracted from resume text."""

    full_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None

    skills: List[str] = []
    top_roles: List[str] = []

    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None

    summary: Optional[str] = None


async def extract_profile_from_resume_llm(resume_text: str) -> ExtractedProfile:
    """
    Extract structured profile data from resume text using LLM.

    Args:
        resume_text: Raw text extracted from resume

    Returns:
        ExtractedProfile with parsed fields

    Raises:
        Exception: If LLM call fails
    """
    try:
        import openai
    except ImportError as e:
        logger.error("openai package not available for resume extraction")
        raise ImportError("openai package required for LLM resume extraction") from e

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set - cannot use LLM extraction")

    model = os.getenv("COMPANION_LLM_MODEL", "gpt-4o-mini")

    system_prompt = (
        "You are a resume parser for ApplyLens. "
        "Given the raw text of a resume, extract a concise JSON object with "
        "career profile fields. Return ONLY valid JSON with no explanations or markdown."
    )

    user_prompt = (
        "Extract the following fields from this resume text:\n\n"
        "full_name (string)\n"
        "headline (short role tagline, e.g. 'AI Engineer & Full-Stack Developer')\n"
        "location (string, city + country if present)\n"
        "years_experience (integer, best estimate; can be null)\n"
        "skills (array of 10-30 key technical skills)\n"
        "top_roles (array of target roles, e.g. ['ML Engineer','Full-Stack Engineer'])\n"
        "github_url (string or null)\n"
        "portfolio_url (string or null)\n"
        "website_url (string or null)\n"
        "linkedin_url (string or null)\n"
        "twitter_url (string or null)\n"
        "summary (2-4 sentence professional summary).\n\n"
        "Return ONLY a JSON object with these keys.\n\n"
        f"Resume text:\n{resume_text[:15000]}"
    )

    try:
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        response_text = response.choices[0].message.content or ""

        # Try to extract JSON from response (handle markdown code blocks)
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        data = json.loads(cleaned.strip())
        logger.info(
            f"LLM extracted profile: {len(data.get('skills', []))} skills, {data.get('full_name', 'N/A')}"
        )

        return ExtractedProfile(**data)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.debug(f"Response text: {response_text}")
        # Return empty profile on parse error
        return ExtractedProfile()
    except Exception as e:
        logger.error(f"LLM resume extraction failed: {e}")
        # Return empty profile on any error
        return ExtractedProfile()


async def parse_resume_text(text: str, llm_callable: Optional[callable] = None) -> dict:
    """Parse resume text into structured data.

    Args:
        text: Raw resume text
        llm_callable: Optional LLM function for intelligent parsing
                     Signature: async def llm(prompt: str) -> str

    Returns:
        Dictionary with keys:
            - headline: str (e.g., "Senior Software Engineer")
            - summary: str (professional summary/objective)
            - skills: list[str] (e.g., ["Python", "React", "AWS"])
            - experiences: list[dict] (company, role, duration, description)
            - projects: list[dict] (name, description, tech_stack)
    """
    if llm_callable:
        return await _parse_with_llm(text, llm_callable)
    else:
        return _parse_with_heuristics(text)


async def _parse_with_llm(text: str, llm_callable: callable) -> dict:
    """Parse resume using LLM for intelligent extraction."""
    prompt = f"""You are a resume parsing assistant. Extract structured information from the following resume text.

Resume text:
{text}

Extract and return a JSON object with the following structure:
{{
  "headline": "Job title or professional headline (e.g., 'Senior Software Engineer')",
  "summary": "Professional summary or objective statement",
  "skills": ["Skill1", "Skill2", "Skill3"],
  "experiences": [
    {{
      "company": "Company Name",
      "role": "Job Title",
      "duration": "Start - End (e.g., 'Jan 2020 - Present')",
      "description": "Brief description of responsibilities"
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Brief project description",
      "tech_stack": ["Tech1", "Tech2"]
    }}
  ]
}}

Return ONLY the JSON object, no other text."""

    response = await llm_callable(prompt)

    # Try to extract JSON from response
    try:
        import json

        # Remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return json.loads(cleaned.strip())
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        # Fallback to heuristics
        return _parse_with_heuristics(text)


def _parse_with_heuristics(text: str) -> dict:
    """Parse resume using heuristic rules (fallback when no LLM available)."""
    lines = text.split("\n")

    # Extract headline (usually first non-empty line or after name)
    headline = None
    for line in lines[:10]:
        line = line.strip()
        # Skip name (all caps or single line)
        if (
            line
            and not line.isupper()
            and len(line) > 10
            and any(
                word in line.lower()
                for word in ["engineer", "developer", "manager", "analyst", "designer"]
            )
        ):
            headline = line
            break

    # Extract skills (look for "Skills" section)
    skills = []
    in_skills_section = False
    for i, line in enumerate(lines):
        if re.match(
            r"^\s*(skills|technical skills|technologies)\s*:?\s*$", line, re.IGNORECASE
        ):
            in_skills_section = True
            continue
        if in_skills_section:
            # End of skills section when we hit another section header
            if re.match(
                r"^\s*(experience|education|projects)\s*:?\s*$", line, re.IGNORECASE
            ):
                break
            # Extract comma or bullet-separated skills
            if line.strip():
                # Remove bullets and split by comma
                cleaned = re.sub(r"^[\s•\-\*]+", "", line)
                parts = [s.strip() for s in re.split(r"[,;|]", cleaned) if s.strip()]
                skills.extend(parts)

    # Extract summary (look for "Summary" or "Objective" section)
    summary = None
    in_summary_section = False
    summary_lines = []
    for i, line in enumerate(lines):
        if re.match(
            r"^\s*(summary|objective|about|profile)\s*:?\s*$", line, re.IGNORECASE
        ):
            in_summary_section = True
            continue
        if in_summary_section:
            # End when we hit another section
            if re.match(
                r"^\s*(skills|experience|education)\s*:?\s*$", line, re.IGNORECASE
            ):
                break
            if line.strip():
                summary_lines.append(line.strip())
    summary = " ".join(summary_lines) if summary_lines else None

    # Extract experiences (simplified - just look for "Experience" section)
    experiences = []
    in_experience_section = False
    current_exp = {}
    for i, line in enumerate(lines):
        if re.match(
            r"^\s*(experience|work experience|employment)\s*:?\s*$", line, re.IGNORECASE
        ):
            in_experience_section = True
            continue
        if in_experience_section:
            # End when we hit another major section
            if re.match(
                r"^\s*(education|projects|skills)\s*:?\s*$", line, re.IGNORECASE
            ):
                if current_exp:
                    experiences.append(current_exp)
                break

            # Try to detect company/role patterns
            # Pattern: "Company Name" or "Job Title at Company"
            if line.strip() and not line.startswith(" "):
                # Save previous experience
                if current_exp:
                    experiences.append(current_exp)
                    current_exp = {}

                # New experience entry
                if " at " in line:
                    parts = line.split(" at ", 1)
                    current_exp = {
                        "role": parts[0].strip(),
                        "company": parts[1].strip(),
                        "duration": "",
                        "description": "",
                    }
                else:
                    current_exp = {
                        "company": line.strip(),
                        "role": "",
                        "duration": "",
                        "description": "",
                    }

    # Extract projects (simplified)
    projects = []
    in_projects_section = False
    current_project = {}
    for i, line in enumerate(lines):
        if re.match(r"^\s*(projects|personal projects)\s*:?\s*$", line, re.IGNORECASE):
            in_projects_section = True
            continue
        if in_projects_section:
            # End when we hit another section
            if re.match(
                r"^\s*(education|skills|experience)\s*:?\s*$", line, re.IGNORECASE
            ):
                if current_project:
                    projects.append(current_project)
                break

            # Project entries often start with project name
            if line.strip() and not line.startswith(" "):
                if current_project:
                    projects.append(current_project)
                current_project = {
                    "name": line.strip(),
                    "description": "",
                    "tech_stack": [],
                }

    return {
        "headline": headline,
        "summary": summary,
        "skills": skills,
        "experiences": experiences,
        "projects": projects,
    }
