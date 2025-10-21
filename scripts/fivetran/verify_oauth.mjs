#!/usr/bin/env node

/**
 * Fivetran OAuth Verification Script
 * 
 * Verifies that the Gmail connector uses Custom OAuth (user-provided OAuth app)
 * instead of Fivetran's shared OAuth application.
 * 
 * Usage:
 *   FIVETRAN_API_KEY=xxx FIVETRAN_API_SECRET=yyy FIVETRAN_CONNECTOR_ID=zzz node verify_oauth.mjs
 */

import { writeFileSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Read environment variables
const API_KEY = process.env.FIVETRAN_API_KEY;
const API_SECRET = process.env.FIVETRAN_API_SECRET;
const CONNECTOR_ID = process.env.FIVETRAN_CONNECTOR_ID;

// Validation
if (!API_KEY || !API_SECRET || !CONNECTOR_ID) {
  console.error('❌ Missing required environment variables!\n');
  console.error('Required:');
  console.error('  FIVETRAN_API_KEY       - Fivetran API key');
  console.error('  FIVETRAN_API_SECRET    - Fivetran API secret');
  console.error('  FIVETRAN_CONNECTOR_ID  - Gmail connector ID\n');
  console.error('Example (PowerShell):');
  console.error('  $env:FIVETRAN_API_KEY="your_key"');
  console.error('  $env:FIVETRAN_API_SECRET="your_secret"');
  console.error('  $env:FIVETRAN_CONNECTOR_ID="connector_id"');
  console.error('  node scripts/fivetran/verify_oauth.mjs\n');
  console.error('Example (Bash):');
  console.error('  export FIVETRAN_API_KEY="your_key"');
  console.error('  export FIVETRAN_API_SECRET="your_secret"');
  console.error('  export FIVETRAN_CONNECTOR_ID="connector_id"');
  console.error('  node scripts/fivetran/verify_oauth.mjs\n');
  process.exit(1);
}

// API endpoint
const API_URL = `https://api.fivetran.com/v1/connectors/${CONNECTOR_ID}`;

// Create Basic Auth header
const authString = Buffer.from(`${API_KEY}:${API_SECRET}`).toString('base64');

console.log('🔍 Verifying Fivetran Gmail OAuth configuration...\n');

/**
 * Detect OAuth type from connector configuration
 */
function detectOAuthType(data) {
  // Check various fields that indicate custom OAuth
  const config = data.config || {};
  const auth = data.authentication || {};
  
  // Common patterns for custom OAuth detection
  const indicators = {
    custom_oauth: false,
    shared_oauth: false,
    auth_type: null,
    evidence: []
  };

  // Check auth_type field
  if (config.auth_type) {
    indicators.auth_type = config.auth_type;
    indicators.evidence.push(`config.auth_type = ${config.auth_type}`);
  }

  // Check for custom OAuth indicators
  if (config.use_own_oauth === true) {
    indicators.custom_oauth = true;
    indicators.evidence.push('config.use_own_oauth = true');
  }
  
  if (config.custom_oauth === true) {
    indicators.custom_oauth = true;
    indicators.evidence.push('config.custom_oauth = true');
  }

  if (auth.method === 'custom_oauth' || auth.method === 'user_provided') {
    indicators.custom_oauth = true;
    indicators.evidence.push(`authentication.method = ${auth.method}`);
  }

  // Check for client_id/client_secret presence (indicates custom OAuth)
  if (config.client_id || config.oauth_client_id) {
    indicators.custom_oauth = true;
    indicators.evidence.push('Custom OAuth client_id detected');
  }

  // Check for shared OAuth indicators
  if (config.use_fivetran_oauth === true || config.use_shared_oauth === true) {
    indicators.shared_oauth = true;
    indicators.evidence.push('Shared OAuth detected');
  }

  return indicators;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(ts) {
  if (!ts) return 'N/A';
  try {
    return new Date(ts).toISOString();
  } catch {
    return ts;
  }
}

/**
 * Check for rate limiting issues in status
 */
function checkRateLimiting(data) {
  const status = data.status || {};
  const setupTests = data.setup_tests || [];
  
  const issues = [];
  
  if (status.setup_state === 'broken' && status.is_historical_sync === false) {
    issues.push('⚠️  Connector setup is broken');
  }
  
  // Check for rate limit errors in setup tests
  for (const test of setupTests) {
    if (test.status === 'FAILED' && test.message) {
      if (test.message.includes('429') || test.message.includes('rateLimitExceeded')) {
        issues.push('⚠️  Rate limiting detected: Reduce history window to 7-14d, increase sync interval, limit labels');
      }
    }
  }
  
  return issues;
}

/**
 * Main verification logic
 */
async function verify() {
  try {
    // Fetch connector details
    console.log(`📡 Fetching connector: ${CONNECTOR_ID}`);
    const response = await fetch(API_URL, {
      method: 'GET',
      headers: {
        'Authorization': `Basic ${authString}`,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ API request failed: ${response.status} ${response.statusText}`);
      console.error(`   Response: ${errorText}`);
      process.exit(1);
    }

    const result = await response.json();
    const data = result.data || {};
    
    // Extract key information
    const service = data.service || 'unknown';
    const connectorId = data.id || CONNECTOR_ID;
    const status = data.status || {};
    const config = data.config || {};
    
    // Detect OAuth type
    const oauthInfo = detectOAuthType(data);
    
    // Determine OAuth status
    let authStatus = 'unknown';
    let isPassing = false;
    
    if (oauthInfo.custom_oauth) {
      authStatus = 'custom_oauth';
      isPassing = true;
    } else if (oauthInfo.shared_oauth) {
      authStatus = 'shared';
      isPassing = false;
    } else if (oauthInfo.evidence.length === 0) {
      authStatus = 'inconclusive';
      isPassing = false;
    }
    
    // Check for rate limiting issues
    const rateLimitIssues = checkRateLimiting(data);
    
    // Print CLI summary
    console.log('─'.repeat(60));
    console.log(`Connector: ${service} / ${connectorId}`);
    console.log(`Auth: ${authStatus}`);
    
    if (oauthInfo.evidence.length > 0) {
      console.log(`Evidence: ${oauthInfo.evidence.join(', ')}`);
    }
    
    console.log(`Last Sync: ${formatTimestamp(status.sync_completed_at)}  Status: ${status.setup_state || 'unknown'}`);
    console.log(`Sync Freq: ${config.sync_frequency || 'N/A'}  History: ${config.history_mode || config.sync_mode || 'N/A'}`);
    
    if (rateLimitIssues.length > 0) {
      console.log('\n⚠️  Issues Detected:');
      rateLimitIssues.forEach(issue => console.log(`   ${issue}`));
    }
    
    console.log('─'.repeat(60));
    
    if (isPassing) {
      console.log('✅ RESULT: PASS (Custom OAuth detected)\n');
    } else if (authStatus === 'shared') {
      console.log('❌ RESULT: FAIL (Shared OAuth detected)\n');
      console.log('Action Required:');
      console.log('  1. Go to Fivetran UI → Connector → Setup');
      console.log('  2. Enable "Use your own OAuth app"');
      console.log('  3. Configure Google OAuth client with redirect URI');
      console.log('  4. Re-authorize and re-run this verifier\n');
      console.log('See: docs/hackathon/FIVETRAN_OAUTH_VERIFY.md\n');
    } else {
      console.log('⚠️  RESULT: INCONCLUSIVE (Unable to determine OAuth type)\n');
      console.log('Manual verification required:');
      console.log('  1. Check Fivetran UI → Connector → Setup → OAuth section');
      console.log('  2. Verify "Use your own OAuth app" is enabled');
      console.log('  3. Review oauth_check.json for raw API response\n');
      console.log('Evidence fields checked:');
      console.log(`  - config.auth_type: ${oauthInfo.auth_type || 'not found'}`);
      console.log(`  - config.use_own_oauth: ${config.use_own_oauth !== undefined ? config.use_own_oauth : 'not found'}`);
      console.log(`  - authentication.method: ${data.authentication?.method || 'not found'}\n`);
    }
    
    // Fetch schema information (optional)
    let schemaInfo = null;
    try {
      console.log('📊 Fetching schema information...');
      const schemaUrl = `https://api.fivetran.com/v1/connectors/${CONNECTOR_ID}/schemas`;
      const schemaResponse = await fetch(schemaUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Basic ${authString}`,
          'Accept': 'application/json'
        }
      });
      
      if (schemaResponse.ok) {
        const schemaResult = await schemaResponse.json();
        const schemas = schemaResult.data?.schemas || [];
        let totalTables = 0;
        let enabledTables = 0;
        
        for (const schema of schemas) {
          const tables = schema.tables || [];
          totalTables += tables.length;
          enabledTables += tables.filter(t => t.enabled).length;
        }
        
        schemaInfo = {
          total_tables: totalTables,
          enabled_tables: enabledTables,
          schemas: schemas.length
        };
        
        console.log(`   Schemas: ${schemaInfo.schemas}, Tables: ${enabledTables}/${totalTables} enabled\n`);
      }
    } catch (err) {
      console.log('   Schema fetch skipped (optional)\n');
    }
    
    // Write evidence file
    const evidenceDir = join(__dirname, '..', '..', 'docs', 'hackathon');
    mkdirSync(evidenceDir, { recursive: true });
    
    const evidencePath = join(evidenceDir, 'EVIDENCE_FIVETRAN_OAUTH.md');
    
    const evidenceContent = `# Fivetran OAuth Verification Evidence

**Verification Date:** ${new Date().toISOString()}  
**Connector ID:** ${connectorId}  
**Service:** ${service}

## Result

**Status:** ${isPassing ? '✅ PASS' : (authStatus === 'shared' ? '❌ FAIL' : '⚠️ INCONCLUSIVE')}  
**Auth Type:** ${authStatus}  
**Custom OAuth Detected:** ${isPassing ? 'Yes' : 'No'}

${oauthInfo.evidence.length > 0 ? `\n**Evidence:**\n${oauthInfo.evidence.map(e => `- ${e}`).join('\n')}\n` : ''}

## Connector Details

- **Service:** ${service}
- **Connector ID:** ${connectorId}
- **Status:** ${status.setup_state || 'unknown'}
- **Last Sync:** ${formatTimestamp(status.sync_completed_at)}
- **Sync Frequency:** ${config.sync_frequency || 'N/A'}
- **History Mode:** ${config.history_mode || config.sync_mode || 'N/A'}

${schemaInfo ? `\n## Schema Information

- **Schemas:** ${schemaInfo.schemas}
- **Total Tables:** ${schemaInfo.total_tables}
- **Enabled Tables:** ${schemaInfo.enabled_tables}
` : ''}

${rateLimitIssues.length > 0 ? `\n## Issues Detected

${rateLimitIssues.map(issue => `- ${issue}`).join('\n')}

**Recommendations:**
- Reduce history window to 7-14 days
- Increase sync interval (e.g., every 6 hours instead of hourly)
- Limit labels synced (exclude promotional, spam, etc.)
- See RUNBOOK.md for configuration details
` : ''}

## API Response (Redacted)

\`\`\`json
${JSON.stringify({
  data: {
    id: data.id,
    service: data.service,
    service_version: data.service_version,
    status: {
      setup_state: status.setup_state,
      sync_state: status.sync_state,
      sync_completed_at: status.sync_completed_at,
      update_state: status.update_state
    },
    config: {
      auth_type: config.auth_type,
      use_own_oauth: config.use_own_oauth,
      custom_oauth: config.custom_oauth,
      sync_frequency: config.sync_frequency,
      history_mode: config.history_mode,
      // Redact sensitive fields
      client_id: config.client_id ? '***REDACTED***' : undefined,
      client_secret: config.client_secret ? '***REDACTED***' : undefined
    },
    authentication: data.authentication ? {
      method: data.authentication.method
    } : undefined
  }
}, null, 2)}
\`\`\`

## Verification Method

This evidence was generated by \`scripts/fivetran/verify_oauth.mjs\`.

**Command:**
\`\`\`bash
FIVETRAN_API_KEY=*** FIVETRAN_API_SECRET=*** FIVETRAN_CONNECTOR_ID=${connectorId} \\
  node scripts/fivetran/verify_oauth.mjs
\`\`\`

## Next Steps

${isPassing ? `
✅ **No action required** - Custom OAuth is properly configured.

**For Devpost submission:**
1. Take screenshot of Fivetran connector setup showing "Use your own OAuth app" enabled
2. Take screenshot of this evidence file
3. Include in hackathon evidence pack
` : (authStatus === 'shared' ? `
❌ **Action Required** - Connector is using shared OAuth.

**To fix:**
1. Open Fivetran UI → Connectors → ${connectorId}
2. Click "Setup" tab
3. Scroll to OAuth section
4. Enable "Use your own OAuth app"
5. Copy the redirect URI provided by Fivetran
6. Go to Google Cloud Console → APIs & Services → Credentials
7. Create/edit OAuth 2.0 client and add redirect URI
8. Copy client ID and secret to Fivetran
9. Re-authorize the connector
10. Re-run this verifier: \`npm run verify:fivetran:oauth\`

**Reference:** docs/hackathon/FIVETRAN_OAUTH_VERIFY.md
` : `
⚠️ **Manual Verification Required** - Could not determine OAuth type from API.

**Steps:**
1. Log into Fivetran UI
2. Navigate to Connectors → ${connectorId}
3. Click "Setup" tab
4. Check OAuth section:
   - If "Use your own OAuth app" is enabled → Custom OAuth ✅
   - If using Fivetran's OAuth app → Shared OAuth ❌
5. Review raw API response in oauth_check.json
6. Update this script if Fivetran API schema has changed

**Evidence checked:**
- \`config.auth_type\`: ${oauthInfo.auth_type || 'not found'}
- \`config.use_own_oauth\`: ${config.use_own_oauth !== undefined ? config.use_own_oauth : 'not found'}
- \`authentication.method\`: ${data.authentication?.method || 'not found'}
`)}

---

**Generated by:** scripts/fivetran/verify_oauth.mjs  
**Timestamp:** ${new Date().toISOString()}
`;

    writeFileSync(evidencePath, evidenceContent, 'utf8');
    console.log(`📄 Evidence written to: ${evidencePath}\n`);
    
    // Write raw JSON for manual inspection
    const jsonPath = join(evidenceDir, 'oauth_check.json');
    writeFileSync(jsonPath, JSON.stringify(result, null, 2), 'utf8');
    console.log(`📄 Raw API response saved to: ${jsonPath}\n`);
    
    // Exit with appropriate code
    process.exit(isPassing ? 0 : 1);
    
  } catch (error) {
    console.error('❌ Error during verification:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// Run verification
verify();
