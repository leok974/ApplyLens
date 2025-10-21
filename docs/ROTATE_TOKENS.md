# Rotate Tokens Cheatsheet

## Grafana

### 1) Revoke old key
- Navigate to Grafana → Configuration → API Keys
- Find the compromised key
- Click "Revoke" to immediately invalidate it

### 2) Create read-only key
- Create new API key with minimal permissions
- Set appropriate expiration date
- Copy the new key immediately (shown only once)

### 3) Update secret in CI/CD
- Update `GRAFANA_API_KEY` in GitHub Actions secrets
- Update any other environments (staging, production)
- Verify secret propagation

### 4) Re-deploy & verify /api/health
- Trigger deployment to pick up new key
- Check `/api/health` endpoint returns 200
- Verify Grafana dashboards are accessible
- Monitor logs for authentication errors

---

## GCP/AWS

### GCP Service Accounts

#### 1) Rotate in console/CLI
```bash
# Create new key
gcloud iam service-accounts keys create new-key.json \
  --iam-account=SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com

# Delete old key (get KEY_ID from list command)
gcloud iam service-accounts keys list \
  --iam-account=SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com
```

#### 2) Update Secret Manager
```bash
# Create new version
gcloud secrets versions add SERVICE_ACCOUNT_KEY \
  --data-file=new-key.json

# Disable old version
gcloud secrets versions disable VERSION_ID \
  --secret=SERVICE_ACCOUNT_KEY
```

#### 3) Restart workloads
```bash
# For Cloud Run
gcloud run services update SERVICE_NAME --region=REGION

# For GKE
kubectl rollout restart deployment/DEPLOYMENT_NAME
```

#### 4) Verify logs & metrics
- Check Cloud Logging for successful auth
- Verify metrics are being exported
- Monitor error rates in Cloud Monitoring

---

### AWS IAM Keys

#### 1) Rotate in console/CLI
```bash
# Create new access key
aws iam create-access-key --user-name USERNAME

# Deactivate old key
aws iam update-access-key --user-name USERNAME \
  --access-key-id OLD_KEY_ID --status Inactive

# Delete old key (after verification)
aws iam delete-access-key --user-name USERNAME \
  --access-key-id OLD_KEY_ID
```

#### 2) Update Secret Manager
```bash
# AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id SECRET_NAME \
  --secret-string '{"access_key":"NEW_KEY","secret_key":"NEW_SECRET"}'
```

#### 3) Restart workloads
```bash
# For ECS
aws ecs update-service --cluster CLUSTER --service SERVICE --force-new-deployment

# For EC2/Auto Scaling
# Update Launch Template with new credentials, then refresh instances
```

#### 4) Verify logs & metrics
- Check CloudWatch Logs for authentication events
- Verify CloudWatch Metrics are flowing
- Monitor CloudTrail for API activity

---

## Emergency Rotation

If a secret is actively being exploited:

1. **Immediate**: Revoke/disable the compromised credential
2. **Within 5 min**: Create and deploy new credential
3. **Within 15 min**: Verify all systems operational with new credential
4. **Within 1 hour**: Review access logs, identify scope of exposure
5. **Within 24 hours**: Complete incident report and post-mortem

---

## Automation

Consider automating rotation:
- GCP: Use Secret Manager rotation with Cloud Scheduler
- AWS: Use Secrets Manager automatic rotation
- GitHub: Use Dependabot alerts for leaked secrets
