# Contributing to ApplyLens

Thank you for your interest in contributing to ApplyLens! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork:**

   ```bash
   git clone https://github.com/YOUR_USERNAME/ApplyLens.git
   cd ApplyLens
   ```

3. **Set up development environment:** See [GETTING_STARTED.md](./GETTING_STARTED.md)
4. **Create a feature branch:**

   ```bash
   git checkout -b feature/my-feature develop
   ```

## Development Workflow

### 1. Make Changes

- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation as needed

### 2. Test Your Changes

```bash
# Backend tests
cd services/api
pytest

# Frontend E2E tests
npm run test:e2e

# Linting
ruff check .
black --check .
npm run lint
```

### 3. Commit

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat(search): add fuzzy matching"
```

**Commit Types:**

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Tests
- `chore:` Build/tooling

### 4. Push and Create PR

```bash
git push origin feature/my-feature
```

Then create a Pull Request on GitHub targeting the `develop` branch.

## Code Style Guidelines

### Python (Backend)

**Formatter:** `black` (line length: 100)

```python
# Good
def calculate_risk_score(
    email: Email, user_weights: List[UserWeight]
) -> float:
    """Calculate risk score using confidence learning.
    
    Args:
        email: Email to score
        user_weights: User-specific feature weights
        
    Returns:
        Risk score between 0 and 100
    """
    features = extract_features(email)
    score = sum(w.weight * f.value for w, f in zip(user_weights, features))
    return normalize_score(score)

# Bad
def calcRisk(e,w):  # Poor naming, no types, no docstring
    return sum([x*y for x,y in zip(w,e)])
```

**Linter:** `ruff`

```bash
ruff check .
ruff check . --fix  # Auto-fix
```

**Type Hints:** Use type annotations for all functions

```python
from typing import List, Optional

def get_emails(
    user_id: str,
    category: Optional[str] = None,
    limit: int = 20
) -> List[Email]:
    ...
```

### TypeScript/React (Frontend)

**Linter:** ESLint with React plugin

```typescript
// Good
interface EmailListProps {
  emails: Email[];
  onSelect: (id: string) => void;
  isLoading?: boolean;
}

export function EmailList({ emails, onSelect, isLoading = false }: EmailListProps) {
  return (
    <div className="space-y-2">
      {emails.map((email) => (
        <EmailCard key={email.id} email={email} onClick={() => onSelect(email.id)} />
      ))}
    </div>
  );
}

// Bad
export function EmailList(props: any) {  // No interface, 'any' type
  return <div>{props.emails.map(e => <div>{e.subject}</div>)}</div>;  // No keys
}
```

**Component Structure:**

```typescript
// 1. Imports
import { useState } from 'react';
import { Button } from '@/components/ui/button';

// 2. Types/Interfaces
interface Props {
  title: string;
}

// 3. Component
export function MyComponent({ title }: Props) {
  // 4. Hooks
  const [count, setCount] = useState(0);
  
  // 5. Event handlers
  const handleClick = () => {
    setCount(count + 1);
  };
  
  // 6. Render
  return (
    <div>
      <h1>{title}</h1>
      <Button onClick={handleClick}>Count: {count}</Button>
    </div>
  );
}
```

### CSS/Tailwind

Use Tailwind utility classes:

```tsx
// Good
<div className="flex items-center justify-between rounded-lg border bg-card p-4 shadow-sm">

// Avoid inline styles
<div style={{ display: 'flex', padding: '16px' }}>  // Bad
```

## Testing Guidelines

### Backend (pytest)

```python
# tests/test_risk_service.py

def test_calculate_risk_score_high_risk(db_session):
    """Risk score should be high for suspicious features."""
    # Arrange
    email = EmailFactory(
        sender_domain="suspicious.com",
        subject="URGENT: Click here now!"
    )
    user_weights = [
        UserWeightFactory(feature="sender_domain:suspicious.com", weight=-50),
        UserWeightFactory(feature="keyword:urgent", weight=-30)
    ]
    
    # Act
    risk_score = calculate_risk_score(email, user_weights)
    
    # Assert
    assert risk_score >= 80, f"Expected high risk, got {risk_score}"


def test_calculate_risk_score_safe_email(db_session):
    """Risk score should be low for trusted senders."""
    email = EmailFactory(sender_domain="linkedin.com")
    user_weights = [
        UserWeightFactory(feature="sender_domain:linkedin.com", weight=100)
    ]
    
    risk_score = calculate_risk_score(email, user_weights)
    
    assert risk_score < 20
```

### Frontend (Playwright)

```typescript
// tests/e2e/email-search.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Email Search', () => {
  test('should filter emails by category', async ({ page }) => {
    await page.goto('http://localhost:5175');
    
    // Select "Application" category
    await page.click('[data-testid="category-filter"]');
    await page.click('text=Application');
    
    // Verify filter applied
    const emails = page.locator('[data-testid="email-card"]');
    await expect(emails).toHaveCount(5);
    
    // Verify all emails are applications
    const categories = await emails.locator('.category-badge').allTextContents();
    expect(categories.every(c => c === 'Application')).toBe(true);
  });
});
```

## Documentation

### Code Comments

```python
# Good: Explain WHY, not WHAT
def normalize_score(raw_score: float) -> float:
    """Normalize raw score to 0-100 range using sigmoid function.
    
    We use sigmoid instead of linear scaling to handle outliers gracefully.
    Extreme values (< -10 or > 10) are smoothly capped at 0 or 100.
    """
    return 100 / (1 + math.exp(-raw_score))

# Bad: States the obvious
def normalize_score(raw_score: float) -> float:
    # Calculate 100 divided by 1 plus e to the power of negative raw_score
    return 100 / (1 + math.exp(-raw_score))
```

### API Documentation

Use OpenAPI/Swagger annotations:

```python
@router.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: UUID,
    db: Session = Depends(get_db)
) -> EmailResponse:
    """
    Get email by ID.
    
    Returns email details including subject, sender, body, risk score,
    and associated application (if any).
    
    **Permissions:** User must own the email.
    
    **Example Response:**
    ```json
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "subject": "Application Received",
      "sender": "hr@company.com",
      "risk_score": 15.3
    }
    ```
    """
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
```

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass
- [ ] Code is formatted (black, ESLint)
- [ ] No linting errors
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for user-facing changes)

### PR Description

Use the [PR template](.github/pull_request_template.md):

```markdown
## Description
Added fuzzy matching to email search for better typo tolerance.

## Type of Change
- [x] New feature

## Changes Made
- Added fuzziness parameter to Elasticsearch multi_match query
- Updated search UI to show "Did you mean?" suggestions
- Added tests for fuzzy search

## Testing
- [x] Unit tests added
- [x] Manual testing performed

**Test Steps:**
1. Search for "sofware" (typo)
2. Verify "software" results are returned
3. Check "Did you mean?" suggestion

## Screenshots
[Before/After images]
```

### Code Review

Be open to feedback and iterate quickly. Reviewers will check:

- Code quality and readability
- Test coverage
- Performance implications
- Security concerns
- Breaking changes

## Reporting Issues

### Bug Reports

Use GitHub Issues with the following template:

```markdown
**Describe the bug**
Risk score calculation returns NaN for certain emails.

**To Reproduce**
1. Sync emails from Gmail
2. Open email with subject "Test"
3. Observe risk score shows "NaN"

**Expected behavior**
Risk score should be a number between 0-100.

**Screenshots**
[If applicable]

**Environment:**
- OS: Windows 11
- Browser: Chrome 120
- ApplyLens version: 1.2.0

**Additional context**
Happens only for emails with no sender_domain.
```

### Feature Requests

```markdown
**Is your feature request related to a problem?**
Difficult to find emails from a specific time period.

**Describe the solution you'd like**
Add date range picker to filter emails.

**Describe alternatives you've considered**
Manual scrolling, but inefficient for large inboxes.

**Additional context**
Calendar UI like Gmail's date filter would be ideal.
```

## Development Tools

### Recommended VS Code Extensions

- **Python:** ms-python.python
- **Pylance:** ms-python.vscode-pylance
- **Ruff:** charliermarsh.ruff
- **ESLint:** dbaeumer.vscode-eslint
- **Prettier:** esbenp.prettier-vscode
- **Tailwind CSS IntelliSense:** bradlc.vscode-tailwindcss

### Pre-commit Hooks

Install pre-commit hooks to catch issues early:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
  
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.55.0
    hooks:
      - id: eslint
        files: \.(js|ts|tsx)$
```

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Questions?

- Check [existing documentation](./README.md)
- Ask in GitHub Discussions
- Open an issue for clarification

Thank you for contributing! 🎉
