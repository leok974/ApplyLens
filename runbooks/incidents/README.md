# Incident Archive

This folder contains write-ups for real production incidents.

Each file includes:
- Root cause
- Remediation
- Prevention / guardrail updates

This is used for on-call readiness, regression prevention, and to show operational maturity.

## Incidents

- [`nginx-503-upstream-resolution.md`](./nginx-503-upstream-resolution.md) - Nginx 503 upstream errors
- [`cloudflare-tunnel-530-error.md`](./cloudflare-tunnel-530-error.md) - Cloudflare tunnel 530 errors
- [`csrf-403-token-mismatch.md`](./csrf-403-token-mismatch.md) - CSRF token validation failures
- [`gmail-api-rate-limit-429.md`](./gmail-api-rate-limit-429.md) - Gmail API rate limiting
- [`postgres-password-encoding-fix.md`](./postgres-password-encoding-fix.md) - Database password encoding issues
- [`oauth-redirect-uri-mismatch.md`](./oauth-redirect-uri-mismatch.md) - OAuth redirect URI configuration
- [`oauth-403-400-debugging.md`](./oauth-403-400-debugging.md) - OAuth authorization errors
- [`elasticsearch-query-performance.md`](./elasticsearch-query-performance.md) - Elasticsearch performance issues
- [`fivetran-rate-limit-analysis.md`](./fivetran-rate-limit-analysis.md) - Fivetran API rate limits
