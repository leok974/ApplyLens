# Secrets Policy

## Core Principles

- **Secrets live in env vars or cloud secret managers (GCP/AWS), never in git.**
- **Redact tokens in docs/screenshots.**
- **Rotate immediately if a secret appears in git history.**

## Rotation Runbook

When a secret is exposed:

### 1) Revoke/rotate in provider
- Immediately invalidate the compromised secret
- Generate new credentials in the provider console/API

### 2) Replace in Secret Manager
- Update the secret value in GCP Secret Manager, AWS Secrets Manager, or your secret store
- Verify the new secret is accessible

### 3) Redeploy with new env
- Trigger deployment to pick up the new secret
- Ensure all services/workloads restart with new credentials

### 4) Purge caches & verify
- Clear any cached credentials
- Test end-to-end functionality
- Verify logs show successful authentication with new credentials
- Monitor for any failed auth attempts using old credentials

## Prevention

- Use `.env.example` with placeholders, never commit `.env`
- Run `pre-commit install` to enable gitleaks scanning
- Review diffs before committing: `git diff --cached`
- Blur credentials in screenshots before committing docs

## Resources

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
