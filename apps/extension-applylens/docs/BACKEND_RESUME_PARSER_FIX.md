# Backend Resume Parser Implementation Guide

## Summary

Fix the 500 error on `/api/resume/upload` and implement reliable PDF parsing with profile field extraction. This enables resume → profile → extension auto-fill flow.

## Current State

✅ **Already Working:**
- Resume upload endpoint exists (`/api/resume/upload`)
- Database schema supports resume profiles
- Frontend upload UI in `ResumeUploadPanel.tsx`
- Tests in `test_resume_endpoints.py`
- Extension already consumes profile fields (github_url, portfolio_url, website_url, location, tech_stack)

❌ **Needs Fixing:**
- 500 error: "Server is missing required dependencies for this file format"
- No PDF parsing implementation (currently only .txt works)
- No skill/link extraction from resume text

## Implementation Steps

### 1. Update pyproject.toml

**File**: `services/api/pyproject.toml`

```toml
[project.dependencies]
# ... existing dependencies ...
pypdf = "^5.0.0"  # For PDF text extraction
```

Or if using requirements.txt:

```txt
pypdf>=5.0.0
```

### 2. Create/Update resume_parser.py

**File**: `services/api/app/services/resume_parser.py`

```python
"""Resume parsing service with PDF support."""

import io
import logging
import re
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Check if pypdf is available
try:
    from pypdf import PdfReader
    RESUME_PARSER_AVAILABLE = True
except ImportError:
    logger.warning("pypdf not installed - PDF parsing disabled")
    RESUME_PARSER_AVAILABLE = False


class ParsedResume(BaseModel):
    """Parsed resume data."""
    raw_text: str
    pages: int


class ExtractedProfile(BaseModel):
    """Extracted profile fields from resume text."""
    skills: list[str] = []
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None


def extract_text_from_resume(filename: str, content: bytes) -> str:
    """Extract text from resume file (PDF, DOCX, or TXT).

    Args:
        filename: Original filename (for extension detection)
        content: File content as bytes

    Returns:
        Extracted text content

    Raises:
        ValueError: If file format is unsupported or parsing fails
        ImportError: If required parser library is missing
    """
    file_ext = '.' + filename.split('.')[-1].lower()

    # Text files - simple decode
    if file_ext == '.txt':
        try:
            return content.decode('utf-8', errors='ignore')
        except Exception as e:
            raise ValueError(f"Failed to decode text file: {e}")

    # PDF files - use pypdf
    elif file_ext == '.pdf':
        if not RESUME_PARSER_AVAILABLE:
            raise ImportError(
                "PDF parsing requires pypdf library. "
                "Install with: pip install pypdf"
            )

        try:
            parsed = parse_pdf_resume(content)
            return parsed.raw_text
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {e}")

    # DOCX files - could add python-docx support later
    elif file_ext == '.docx':
        raise ValueError(
            "DOCX parsing not yet implemented. "
            "Please convert to PDF or TXT for now."
        )

    else:
        raise ValueError(f"Unsupported file format: {file_ext}")


def parse_pdf_resume(data: bytes) -> ParsedResume:
    """Parse PDF resume and extract text.

    Args:
        data: PDF file content as bytes

    Returns:
        ParsedResume with raw text and page count

    Raises:
        ImportError: If pypdf is not installed
        ValueError: If PDF cannot be parsed
    """
    if not RESUME_PARSER_AVAILABLE:
        raise ImportError("pypdf library not available")

    try:
        reader = PdfReader(io.BytesIO(data))
        text_parts = []

        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                text_parts.append(txt.strip())

        raw_text = "\n\n".join(text_parts)

        if not raw_text.strip():
            raise ValueError("PDF appears to be empty or contains only images")

        return ParsedResume(
            raw_text=raw_text,
            pages=len(reader.pages)
        )
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise ValueError(f"Could not parse PDF: {e}")


def extract_profile_fields_from_text(text: str) -> ExtractedProfile:
    """Extract profile fields from resume text using heuristics.

    Args:
        text: Resume text content

    Returns:
        ExtractedProfile with extracted skills, links, location

    Note:
        This is a simple heuristic implementation.
        Future: Replace with LLM-based extraction for better accuracy.
    """
    extracted = ExtractedProfile()

    # 1. Extract URLs from text
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)

    for url in urls:
        url_lower = url.lower()

        # GitHub
        if 'github.com/' in url_lower and not extracted.github_url:
            # Clean trailing punctuation
            cleaned = url.rstrip('.,;)')
            extracted.github_url = cleaned

        # LinkedIn (if we want to extract it)
        elif 'linkedin.com/in/' in url_lower:
            pass  # Already handled by resume_profile_parser

        # Portfolio/Personal Website
        elif any(domain in url_lower for domain in ['leoklemet.com', 'portfolio']):
            if not extracted.portfolio_url:
                extracted.portfolio_url = url.rstrip('.,;)')

        # Generic website (last resort)
        elif not url_lower.startswith('http://localhost') and not extracted.website_url:
            # Skip common platforms, keep personal domains
            skip_domains = ['linkedin.com', 'github.com', 'twitter.com', 'facebook.com']
            if not any(d in url_lower for d in skip_domains):
                extracted.website_url = url.rstrip('.,;)')

    # 2. Extract skills (simple keyword matching)
    # Future: Replace with LLM extraction for better accuracy
    common_skills = [
        'Python', 'JavaScript', 'TypeScript', 'React', 'Vue', 'Angular',
        'Node.js', 'FastAPI', 'Django', 'Flask', 'Express',
        'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
        'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
        'Git', 'CI/CD', 'REST', 'GraphQL', 'Microservices',
        'Machine Learning', 'Data Science', 'AI',
        'HTML', 'CSS', 'Tailwind', 'Bootstrap',
        'SQL', 'NoSQL', 'Linux', 'Bash'
    ]

    found_skills = set()
    text_lower = text.lower()

    for skill in common_skills:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill)

    extracted.skills = sorted(list(found_skills))

    # 3. Extract location (simple heuristic)
    # Look for patterns like "Location: City, ST" or "City, State"
    location_patterns = [
        r'Location:\s*([A-Z][a-zA-Z\s]+,\s*[A-Z]{2})',
        r'([A-Z][a-zA-Z\s]+,\s*[A-Z]{2},?\s*(?:United States|USA)?)',
    ]

    for pattern in location_patterns:
        match = re.search(pattern, text)
        if match:
            extracted.location = match.group(1).strip()
            break

    logger.info(
        f"Extracted from resume: {len(extracted.skills)} skills, "
        f"GitHub={bool(extracted.github_url)}, "
        f"Portfolio={bool(extracted.portfolio_url)}, "
        f"Location={bool(extracted.location)}"
    )

    return extracted


# Backward compatibility
async def parse_resume_text(text: str, llm_callable=None):
    """Parse resume text (existing function signature).

    Returns structured resume data (headline, summary, skills, etc.)
    This is called by the upload endpoint.
    """
    # Simple heuristic parsing for now
    lines = text.split('\n')

    # Try to extract headline (usually first few lines)
    headline = None
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) < 100 and not line.startswith(('Email:', 'Phone:', 'http')):
            headline = line
            break

    # Extract summary (look for SUMMARY, ABOUT, PROFILE sections)
    summary = None
    summary_keywords = ['summary', 'about', 'profile', 'objective']
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in summary_keywords):
            # Take next few lines as summary
            summary_lines = []
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip() and not lines[j].strip().isupper():
                    summary_lines.append(lines[j].strip())
                elif lines[j].strip().isupper():  # Hit next section
                    break
            summary = ' '.join(summary_lines)[:500]  # Limit length
            break

    # Use profile field extraction for skills
    extracted = extract_profile_fields_from_text(text)

    return {
        "headline": headline,
        "summary": summary,
        "skills": extracted.skills,
        "experiences": [],  # TODO: Parse work experience
        "projects": [],     # TODO: Parse projects
    }
```

### 3. Update Resume Upload Endpoint

**File**: `services/api/app/routers/resume.py`

Find the `ImportError` handler (around line 125) and change it from 500 → 503:

```python
    except ImportError as e:
        # Server configuration error - missing dependencies
        logger.error(f"Missing dependency for file parsing: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # Changed from 500
            detail="Resume parsing is currently disabled on this server. PDF support requires additional dependencies.",
        )
```

### 4. Merge Extracted Fields into Profile

**File**: `services/api/app/routers/resume.py`

Update the upload endpoint to extract and merge profile fields (around line 140):

```python
    # Extract profile fields from resume text
    from app.services.resume_parser import extract_profile_fields_from_text

    extracted_profile = extract_profile_fields_from_text(raw_text)

    # Parse resume text (heuristic for now, LLM integration later)
    try:
        parsed_data = await parse_resume_text(raw_text, llm_callable=None)
    except Exception as e:
        logger.error(f"Failed to parse resume text: {e}")
        # Continue with empty parsed data - we still save raw text
        parsed_data = {
            "headline": None,
            "summary": None,
            "skills": [],
            "experiences": [],
            "projects": [],
        }

    # Merge extracted skills
    all_skills = list(set(parsed_data.get("skills", []) + extracted_profile.skills))
    parsed_data["skills"] = sorted(all_skills)

    # Parse contact information from resume
    parsed_contact = parse_contact_from_resume(raw_text)

    # Also merge extracted links into contact
    if extracted_profile.github_url and not parsed_contact.github:
        parsed_contact.github = extracted_profile.github_url
    if extracted_profile.portfolio_url and not parsed_contact.portfolio:
        parsed_contact.portfolio = extracted_profile.portfolio_url
    if extracted_profile.website_url and not parsed_contact.website:
        parsed_contact.website = extracted_profile.website_url

    logger.info(
        f"Parsed contact from resume: name={parsed_contact.full_name}, "
        f"email={parsed_contact.email}, phone={parsed_contact.phone}, "
        f"linkedin={parsed_contact.linkedin}, github={parsed_contact.github}, "
        f"portfolio={parsed_contact.portfolio}, years_experience={parsed_contact.years_experience}"
    )
```

### 5. Update Profile Model (if needed)

**File**: `services/api/app/models.py`

Ensure `ResumeProfile` model has these fields:

```python
class ResumeProfile(Base):
    __tablename__ = "resume_profiles"

    # ... existing fields ...

    # Contact fields
    github: Optional[str] = Column(String, nullable=True)
    portfolio: Optional[str] = Column(String, nullable=True)
    website: Optional[str] = Column(String, nullable=True)

    # ... rest of model ...
```

### 6. Add Smoke Test

**File**: `services/api/tests/test_resume_upload.py` (new file)

```python
"""Smoke tests for resume upload with PDF parsing."""

import io
import pytest
from fastapi.testclient import TestClient

# Import after setting test env vars
import os
os.environ["CSRF_ENABLED"] = "false"

from app.main import app

client = TestClient(app)


@pytest.mark.smoke
def test_resume_parser_available():
    """Check if resume parser is available."""
    from app.services import resume_parser

    if not resume_parser.RESUME_PARSER_AVAILABLE:
        pytest.skip("Resume parser (pypdf) not installed")

    assert resume_parser.RESUME_PARSER_AVAILABLE is True


@pytest.mark.smoke
def test_pdf_parsing_smoke():
    """Test basic PDF parsing works."""
    from app.services import resume_parser

    if not resume_parser.RESUME_PARSER_AVAILABLE:
        pytest.skip("Resume parser disabled")

    # Minimal valid PDF
    minimal_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Resume) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
306
%%EOF"""

    # Should not raise
    parsed = resume_parser.parse_pdf_resume(minimal_pdf)
    assert parsed.pages == 1
    assert len(parsed.raw_text) > 0


@pytest.mark.smoke
def test_upload_pdf_endpoint():
    """Test PDF upload via API endpoint."""
    from app.services import resume_parser

    if not resume_parser.RESUME_PARSER_AVAILABLE:
        pytest.skip("Resume parser disabled")

    # Simple PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF"

    files = {"file": ("resume.pdf", io.BytesIO(pdf_content), "application/pdf")}

    resp = client.post(
        "/api/resume/upload",
        files=files,
        headers={
            "X-User-Email": "test@applylens.com",
            "Authorization": "Bearer test-token",
        }
    )

    # May return 400 (invalid PDF) or 201 (success)
    # Both are OK - we're just checking no 500
    assert resp.status_code in (200, 201, 400), f"Unexpected status: {resp.status_code}, body: {resp.text}"
    assert resp.status_code != 500


@pytest.mark.smoke
def test_profile_field_extraction():
    """Test skill/link extraction from resume text."""
    from app.services.resume_parser import extract_profile_fields_from_text

    sample_text = """
    John Doe
    Software Engineer

    Email: john@example.com
    GitHub: https://github.com/johndoe
    Portfolio: https://johndoe.com

    SKILLS
    Python, JavaScript, React, Docker, PostgreSQL

    EXPERIENCE
    Senior Developer at TechCorp (2020-2025)
    Built scalable web applications using FastAPI and React
    """

    extracted = extract_profile_fields_from_text(sample_text)

    assert extracted.github_url == "https://github.com/johndoe"
    assert extracted.portfolio_url == "https://johndoe.com"
    assert "Python" in extracted.skills
    assert "React" in extracted.skills
```

## Deployment Steps

### Local Testing

```bash
cd services/api

# Install dependency
poetry add pypdf
# or: pip install pypdf

# Run tests
pytest tests/test_resume_upload.py -v

# Start server
poetry run uvicorn app.main:app --reload

# Test upload
curl -X POST http://localhost:8000/api/resume/upload \
  -H "X-User-Email: test@applylens.com" \
  -H "Authorization: Bearer test-token" \
  -F "file=@path/to/resume.pdf"
```

### Production Deployment

1. **Update dependencies**:
   ```bash
   cd services/api
   poetry add pypdf
   poetry export -f requirements.txt --output requirements.txt
   ```

2. **Deploy backend**:
   ```bash
   git add services/api/pyproject.toml services/api/poetry.lock
   git commit -m "Add pypdf for resume PDF parsing"
   git push
   ```

3. **Verify deployment**:
   ```bash
   # Check parser availability
   curl https://applylens.app/api/resume/upload \
     -X POST \
     -F "file=@test.pdf" \
     -H "Authorization: Bearer YOUR_TOKEN"

   # Should return 201 (success) or 400 (bad file)
   # NOT 500 or 503
   ```

## Extension Benefits (Already Wired)

Once deployed, the extension automatically gets:

✅ **Auto-fill from Resume:**
- GitHub URL (from resume → profile → extension)
- Portfolio URL (from resume → profile → extension)
- Website URL (from resume → profile → extension)
- Location (from resume → profile → extension)

✅ **Better AI Answers:**
- `profile.tech_stack` includes skills extracted from resume
- LLM context is richer (more skills, projects in profile)
- Answers feel more "you" vs generic

✅ **No Extension Changes Needed:**
- `contentV2.js` already uses `getProfileValue()` for all fields
- `buildLLMProfileContext()` already includes tech_stack
- Purple "Profile" badges already show for profile-backed fields

## Future Enhancements

### Phase 2: LLM-Based Extraction (Later)

Replace heuristic extraction with Claude/GPT for better accuracy:

```python
async def extract_with_llm(resume_text: str) -> ExtractedProfile:
    """Use LLM to extract profile fields from resume."""

    prompt = f"""Extract structured data from this resume:

{resume_text}

Return JSON with:
- skills: list of technical skills (["Python", "React", ...])
- github_url: GitHub profile URL (if found)
- portfolio_url: Portfolio/personal website (if found)
- location: Current location (City, State format)
- summary: 2-3 sentence professional summary

Return only JSON, no explanations."""

    response = await call_llm(prompt)
    return ExtractedProfile(**json.loads(response))
```

### Phase 3: DOCX Support

Add python-docx:

```python
from docx import Document

def parse_docx_resume(data: bytes) -> ParsedResume:
    doc = Document(io.BytesIO(data))
    text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
    raw_text = "\n".join(text_parts)
    return ParsedResume(raw_text=raw_text, pages=len(doc.sections))
```

## Testing Checklist

- [ ] pypdf installed (`poetry show pypdf`)
- [ ] Smoke tests pass (`pytest -m smoke tests/test_resume_upload.py`)
- [ ] Upload PDF returns 201 (not 500)
- [ ] Profile updated with GitHub/portfolio from resume
- [ ] Extension auto-fills GitHub/portfolio on job forms
- [ ] Skills in profile match resume skills
- [ ] LLM answers use skills from resume

## Rollback Plan

If issues occur:

1. **Disable PDF parsing**:
   ```python
   RESUME_PARSER_AVAILABLE = False  # Force disable
   ```

2. **Revert to text-only**:
   ```python
   allowed_extensions = {".txt"}  # Remove .pdf
   ```

3. **Database rollback** (if schema changed):
   ```bash
   alembic downgrade -1
   ```

## Success Metrics

After deployment:

- ✅ Resume upload success rate > 90%
- ✅ Profile completion rate increases (more fields filled)
- ✅ Extension auto-fill rate increases (fewer manual fills)
- ✅ AI answer quality improves (uses resume context)
- ✅ No 500 errors on `/api/resume/upload`

---

**Next Steps**: Copy this to backend repo and implement. Extension is already ready to consume the enriched profile! 🚀
