# Secrets Hygiene Policy

**Version:** 1.0  
**Last Updated:** October 20, 2025  
**Status:** Active

## 🔐 Overview

This document outlines ApplyLens' policy for handling secrets, credentials, and sensitive data in our codebase and documentation.

---

## 📜 Policy

### ❌ Never Commit

The following should **NEVER** be committed to the repository:

1. **API Keys & Tokens**
   - Grafana API keys (`eyJr...`)
   - OAuth client secrets
   - Service account credentials
   - Personal access tokens (GitHub, etc.)

2. **Passwords & Credentials**
   - Database passwords
   - Admin passwords
   - Encryption keys (production)
   - Private keys (`.pem`, `.key` files)

3. **Configuration with Secrets**
   - `.env` files with real credentials
   - `secrets.yaml` or similar
   - AWS credentials (`~/.aws/credentials`)
   - GCP service account JSON files

4. **Sensitive URLs**
   - Production database connection strings with embedded passwords
   - Private webhook URLs with tokens

### ✅ Safe Practices

**Use these instead:**

1. **Environment Variables**
   ```python
   # ✅ Good
   api_key = os.getenv("GRAFANA_API_KEY")
   
   # ❌ Bad
   api_key = "eyJrIjoidXo3ekFBUzdjcUR1Z3E0UzR6QmFm..."
   ```

2. **Example Configurations**
   ```bash
   # .env.example (✅ Safe to commit)
   GRAFANA_API_KEY=your_grafana_api_key_here
   DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   
   # .env (❌ Never commit)
   GRAFANA_API_KEY=eyJrIjoidXo3ekFBUzdjcUR1Z3E0UzR6QmFm...
   DATABASE_URL=postgresql://admin:Sup3rS3cr3t@prod.db.internal:5432/applylens
   ```

3. **Redacted Documentation**
   ```markdown
   # ✅ Good
   **API Key:** [REDACTED - Generate new key in Grafana]
   
   # ✅ Also Good
   **API Key:** YOUR_GRAFANA_API_KEY
   
   # ❌ Bad
   **API Key:** eyJrIjoidXo3ekFBUzdjcUR1Z3E0UzR6QmFm...
   ```

4. **Safe Screenshots**
   - **Blur/redact** API keys, tokens, emails in screenshots
   - Use **placeholder data** (e.g., `demo@applylens.app`)
   - Avoid showing full connection strings

---

## 🛠️ Tools & Automation

### Pre-commit Hooks

We use **gitleaks** to scan for secrets before commits:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### CI/CD Scanning

GitHub Actions runs gitleaks on every PR and push:
- **Workflow:** `.github/workflows/secret-scan.yml`
- **Fails if:** Secrets detected
- **SARIF upload:** Results appear in Security tab

### Local Scanning

Scan your changes before committing:

```bash
# Using gitleaks directly
gitleaks detect --source . --no-git -v

# Using Docker (no install needed)
docker run -v $(pwd):/path zricethezav/gitleaks:latest detect --source /path --no-git -v
```

---

## 🚨 What to Do If You Commit a Secret

### Immediate Actions

1. **Revoke the Secret Immediately**
   - Generate a new API key/token
   - Disable the compromised credential
   - **Do not wait** for code fixes

2. **Remove from Git History**
   ```bash
   # Option 1: Amend last commit (if not pushed)
   git add -A
   git commit --amend --no-edit
   git push --force-with-lease
   
   # Option 2: Use BFG Repo-Cleaner (if already pushed)
   brew install bfg
   bfg --replace-text secrets.txt  # File with patterns to replace
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```

3. **Report to Security**
   - Create incident report
   - Document what was exposed
   - List affected systems
   - Timeline of exposure

### Prevention

- **Enable GitHub Secret Scanning**: Already active for this repo
- **Use `.gitignore`**: Ensure sensitive files are ignored
- **Review before pushing**: Always check `git diff --cached`
- **Run pre-commit**: Let automation catch issues

---

## 📋 Checklist for Documentation

Before committing documentation with examples:

- [ ] All API keys/tokens are `[REDACTED]` or `YOUR_*_HERE`
- [ ] No real email addresses (use `demo@applylens.app`)
- [ ] Connection strings use localhost or placeholders
- [ ] Screenshots have sensitive data blurred
- [ ] No OAuth client secrets visible
- [ ] No production URLs with embedded secrets

---

## 🔍 Common Patterns to Watch

Gitleaks detects these patterns:

| Pattern | Example | Fix |
|---------|---------|-----|
| JWT Tokens | `eyJhbGciOiJIUzI1NiIs...` | Use `[JWT_TOKEN]` |
| Base64 Keys | `eyJrIjoidXo3ekFBUzdj...` | Use `[BASE64_KEY]` |
| AWS Keys | `AKIA...` | Use env vars |
| GitHub PAT | `ghp_...` | Use GitHub Actions secrets |
| Database URLs | `postgresql://user:pass@host/db` | Use `[DATABASE_URL]` |

---

## 📚 References

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

## 📞 Contact

Questions about secrets management?
- **Team Lead:** Leo Klemet
- **Security:** Create issue with `security` label
- **Incident:** Follow incident response runbook

---

**Remember:** When in doubt, **redact it out**! 🔒
