"""Resume parsing service for text extraction and structured data extraction.

Supports PDF, DOCX, and plain text formats.
Uses LLM for intelligent parsing of resume structure.
"""

import io
import logging
import re
from typing import Optional

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
    except ImportError:
        raise ImportError(
            "PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2"
        )

    pdf_file = io.BytesIO(content)
    reader = PdfReader(pdf_file)

    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)

    return "\n\n".join(text_parts)


def _extract_from_docx(content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx is required for DOCX extraction. Install with: pip install python-docx"
        )

    docx_file = io.BytesIO(content)
    doc = Document(docx_file)

    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text)

    return "\n".join(text_parts)


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
