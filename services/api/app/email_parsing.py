# Email parsing heuristics for Application auto-fill
# This module can be imported by the /applications/from-email endpoint
# to infer company, role, and source from Gmail message metadata.

import re
from email.utils import parseaddr


def extract_company(sender: str, body_text: str = "", subject: str = "") -> str:
    """Infer company from sender or email body."""
    if not sender:
        return "(Unknown)"
    name, addr = parseaddr(sender)
    # e.g., careers@openai.com → openai
    domain_part = addr.split("@")[-1].split(".")[0] if "@" in addr else ""
    candidates = [name, domain_part]
    # fallback: look for 'at X' in body
    m = re.search(r"at ([A-Z][A-Za-z0-9&\-]+)", body_text)
    if m:
        candidates.append(m.group(1))
    candidates = [c for c in candidates if c and len(c) > 2]
    if not candidates:
        return "(Unknown)"
    # heuristic: prefer proper name
    best = sorted(candidates, key=lambda x: (x.islower(), -len(x)))[0]
    return best.strip()


def extract_role(subject: str = "", body_text: str = "") -> str:
    """Infer job role from subject line or message body."""
    patterns = [
        r"for ([A-Z][A-Za-z0-9 /&\-]+) role",
        r"Position: ([A-Z][A-Za-z0-9 /&\-]+)",
        r"Job: ([A-Z][A-Za-z0-9 /&\-]+)",
    ]
    for pat in patterns:
        for text in (subject, body_text):
            m = re.search(pat, text, flags=re.I)
            if m:
                return m.group(1).strip()
    # fallback: extract phrase after 'Application for'
    m = re.search(r"Application for ([A-Z][A-Za-z0-9 /&\-]+)", subject, flags=re.I)
    if m:
        return m.group(1).strip()
    return "(Unknown Role)"


def extract_source(headers: dict, sender: str, subject: str, body_text: str) -> str:
    """Guess where the email originated from (LinkedIn, Lever, Greenhouse, etc)."""
    joined = f"{subject} {body_text} {sender}".lower()
    if any(k in joined for k in ["lever.co", "via lever"]):
        return "Lever"
    if any(k in joined for k in ["greenhouse.io", "via greenhouse"]):
        return "Greenhouse"
    if "linkedin" in joined:
        return "LinkedIn"
    if "workday" in joined:
        return "Workday"
    if "indeed" in joined:
        return "Indeed"
    return "Email"


# Example usage within from-email endpoint
if __name__ == "__main__":
    sample = {
        "sender": "Careers <careers@openai.com>",
        "subject": "Your Application for Research Engineer role at OpenAI",
        "body": "Thank you for applying for the Research Engineer position at OpenAI!",
        "headers": {},
    }
    print(
        {
            "company": extract_company(
                sample["sender"], sample["body"], sample["subject"]
            ),
            "role": extract_role(sample["subject"], sample["body"]),
            "source": extract_source(
                sample["headers"], sample["sender"], sample["subject"], sample["body"]
            ),
        }
    )
