# Test Pipeline v2 Smart Flags in Kibana
# Run this script to verify pipeline v2 flags are working

$ES_URL = "http://localhost:9200"
$INDEX = "gmail_emails"

Write-Host "`n╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                  ║" -ForegroundColor Cyan
Write-Host "║           📧 Pipeline v2 Smart Flags Query Tests                ║" -ForegroundColor Cyan
Write-Host "║                                                                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "Testing against index: " -NoNewline
Write-Host $INDEX -ForegroundColor Yellow
Write-Host ""

# Helper function to run query and display results
function Test-Query {
    param(
        [string]$Name,
        [string]$Query,
        [string]$Description
    )
    
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "Test: " -NoNewline
    Write-Host $Name -ForegroundColor Yellow
    Write-Host "Query: " -NoNewline
    Write-Host $Query -ForegroundColor White
    Write-Host "Description: $Description" -ForegroundColor Gray
    Write-Host ""
    
    $body = @{
        query = @{
            query_string = @{
                query = $Query
            }
        }
        size = 3
        _source = @("from", "subject", "is_recruiter", "has_calendar_invite", "has_attachment", "company_guess", "is_interview", "is_offer", "received_at")
    } | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri "$ES_URL/$INDEX/_search" -Method Post -Body $body -ContentType "application/json"
        $count = $response.hits.total.value
        
        Write-Host "Results: " -NoNewline
        Write-Host "$count documents" -ForegroundColor Green
        
        if ($count -gt 0) {
            Write-Host "`nSample documents:" -ForegroundColor Cyan
            foreach ($hit in $response.hits.hits) {
                $doc = $hit._source
                Write-Host "  • From: " -NoNewline -ForegroundColor Gray
                Write-Host $doc.from -ForegroundColor White
                Write-Host "    Subject: " -NoNewline -ForegroundColor Gray
                Write-Host $doc.subject -ForegroundColor White
                if ($doc.is_recruiter) {
                    Write-Host "    🎯 is_recruiter: " -NoNewline -ForegroundColor Gray
                    Write-Host "true" -ForegroundColor Green
                }
                if ($doc.has_calendar_invite) {
                    Write-Host "    📅 has_calendar_invite: " -NoNewline -ForegroundColor Gray
                    Write-Host "true" -ForegroundColor Green
                }
                if ($doc.has_attachment) {
                    Write-Host "    📎 has_attachment: " -NoNewline -ForegroundColor Gray
                    Write-Host "true" -ForegroundColor Green
                }
                if ($doc.company_guess) {
                    Write-Host "    🏢 company_guess: " -NoNewline -ForegroundColor Gray
                    Write-Host $doc.company_guess -ForegroundColor Yellow
                }
                if ($doc.is_interview) {
                    Write-Host "    💼 is_interview: " -NoNewline -ForegroundColor Gray
                    Write-Host "true" -ForegroundColor Green
                }
                if ($doc.is_offer) {
                    Write-Host "    🎉 is_offer: " -NoNewline -ForegroundColor Gray
                    Write-Host "true" -ForegroundColor Green
                }
                Write-Host ""
            }
        } else {
            Write-Host "  ℹ️  No documents match this query yet" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "❌ Query failed: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Test 1: Recruiter emails
Test-Query `
    -Name "Recruiter Emails" `
    -Query "is_recruiter:true" `
    -Description "Emails from recruiters (recruit@, careers@, talent@, hr@)"

# Test 2: Recruiter emails with calendar invites
Test-Query `
    -Name "Interview Scheduling" `
    -Query "is_recruiter:true AND has_calendar_invite:true" `
    -Description "Recruiter emails containing calendar invites"

# Test 3: Active opportunities
Test-Query `
    -Name "Active Opportunities" `
    -Query "(is_offer:true OR is_interview:true) AND archived:false" `
    -Description "Unarchived offers and interviews"

# Test 4: Emails with attachments
Test-Query `
    -Name "Emails with Attachments" `
    -Query "has_attachment:true" `
    -Description "All emails containing attachments"

# Test 5: Company-specific search
Test-Query `
    -Name "Company Emails" `
    -Query "company_guess:*" `
    -Description "Emails with extracted company names"

# Test 6: Interview emails
Test-Query `
    -Name "Interview Emails" `
    -Query "is_interview:true" `
    -Description "Emails identified as interview-related"

# Test 7: Offer emails
Test-Query `
    -Name "Offer Emails" `
    -Query "is_offer:true" `
    -Description "Emails identified as job offers"

# Test 8: Complete interview packages
Test-Query `
    -Name "Complete Interview Packages" `
    -Query "is_interview:true AND has_calendar_invite:true AND has_attachment:true" `
    -Description "Interviews with calendar and attachments"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "`n✅ Query tests complete!" -ForegroundColor Green
Write-Host "`nℹ️  Note: If results show 0 or flags are missing, you may need to:" -ForegroundColor Yellow
Write-Host "   1. Reindex existing data through pipeline v2" -ForegroundColor White
Write-Host "   2. Or index new emails which will automatically use v2" -ForegroundColor White
Write-Host "`nSee docs/PIPELINE_V2_VALIDATION_2025-10-20.md for backfill instructions`n" -ForegroundColor Gray
