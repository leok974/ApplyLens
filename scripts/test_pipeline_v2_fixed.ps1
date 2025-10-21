# Test Pipeline v2 Smart Flags
# Run queries against gmail_emails_v2_final index

$ES_URL = "http://localhost:9200"
$INDEX = "gmail_emails_v2_final"

Write-Host "`n" -NoNewline
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Pipeline v2 Smart Flags - Query Tests" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Helper function
function Test-Query {
    param($name, $query)
    Write-Host "[Test] $name" -ForegroundColor Yellow
    try {
        $result = Invoke-RestMethod -Uri "$ES_URL/$INDEX/_search" -Method Post -Body $query -ContentType "application/json"
        $total = $result.hits.total.value
        Write-Host "  Found: $total documents" -ForegroundColor Green
        
        if ($total -gt 0) {
            $result.hits.hits | Select-Object -First 3 | ForEach-Object {
                $doc = $_._source
                Write-Host "  - From: $($doc.sender)" -ForegroundColor Gray
                Write-Host "    Subject: $($doc.subject)" -ForegroundColor Gray
                Write-Host "    Flags: recruit=$($doc.is_recruiter), interview=$($doc.is_interview), calendar=$($doc.has_calendar_invite), company=$($doc.company_guess)" -ForegroundColor Gray
                Write-Host ""
            }
        }
    }
    catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
    }
    Write-Host ""
}

# Test 1: Recruiter Emails
Write-Host "1. Searching for recruiter emails..." -ForegroundColor Cyan
$query1 = @{
    query = @{
        bool = @{
            should = @(
                @{term = @{is_recruiter = $true}},
                @{wildcard = @{sender = "*recruit*"}},
                @{wildcard = @{sender = "*talent*"}}
            )
        }
    }
    size = 5
} | ConvertTo-Json -Depth 10
Test-Query "Recruiter Emails" $query1

# Test 2: Interview-Related
Write-Host "2. Searching for interview-related emails..." -ForegroundColor Cyan
$query2 = @{
    query = @{
        term = @{is_interview = $true}
    }
    size = 5
} | ConvertTo-Json -Depth 10
Test-Query "Interview Emails" $query2

# Test 3: Calendar Invites
Write-Host "3. Searching for emails with calendar invites..." -ForegroundColor Cyan
$query3 = @{
    query = @{
        term = @{has_calendar_invite = $true}
    }
    size = 5
} | ConvertTo-Json -Depth 10
Test-Query "Calendar Invites" $query3

# Test 4: Specific Company
Write-Host "4. Searching for emails from specific companies..." -ForegroundColor Cyan
$query4 = @{
    query = @{
        bool = @{
            must = @(
                @{exists = @{field = "company_guess"}}
            )
        }
    }
    aggs = @{
        top_companies = @{
            terms = @{
                field = "company_guess.keyword"
                size = 10
            }
        }
    }
    size = 0
} | ConvertTo-Json -Depth 10

Write-Host "[Test] Top Companies by Email Count" -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "$ES_URL/$INDEX/_search" -Method Post -Body $query4 -ContentType "application/json"
    $companies = $result.aggregations.top_companies.buckets
    Write-Host "  Top $($companies.Count) companies:" -ForegroundColor Green
    $companies | ForEach-Object {
        Write-Host "  - $($_.key): $($_.doc_count) emails" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
}
Write-Host ""

# Test 5: Combined Query - Recruiter + Interview
Write-Host "5. Searching for recruiter emails about interviews..." -ForegroundColor Cyan
$query5 = @{
    query = @{
        bool = @{
            must = @(
                @{term = @{is_recruiter = $true}},
                @{term = @{is_interview = $true}}
            )
        }
    }
    size = 5
} | ConvertTo-Json -Depth 10
Test-Query "Recruiter Interview Emails" $query5

# Summary Statistics
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Summary Statistics" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$statsQuery = @{
    size = 0
    aggs = @{
        total = @{value_count = @{field = "_id"}}
        recruiters = @{filter = @{term = @{is_recruiter = $true}}}
        interviews = @{filter = @{term = @{is_interview = $true}}}
        calendar_invites = @{filter = @{term = @{has_calendar_invite = $true}}}
        has_company = @{filter = @{exists = @{field = "company_guess"}}}
    }
} | ConvertTo-Json -Depth 10

try {
    $stats = Invoke-RestMethod -Uri "$ES_URL/$INDEX/_search" -Method Post -Body $statsQuery -ContentType "application/json"
    $aggs = $stats.aggregations
    
    Write-Host "Total Emails: $($aggs.total.value)" -ForegroundColor White
    Write-Host "Recruiter Emails: $($aggs.recruiters.doc_count) ($([math]::Round($aggs.recruiters.doc_count * 100 / $aggs.total.value, 1))%)" -ForegroundColor Green
    Write-Host "Interview Emails: $($aggs.interviews.doc_count) ($([math]::Round($aggs.interviews.doc_count * 100 / $aggs.total.value, 1))%)" -ForegroundColor Green
    Write-Host "With Calendar Invites: $($aggs.calendar_invites.doc_count) ($([math]::Round($aggs.calendar_invites.doc_count * 100 / $aggs.total.value, 1))%)" -ForegroundColor Green
    Write-Host "With Company Identified: $($aggs.has_company.doc_count) ($([math]::Round($aggs.has_company.doc_count * 100 / $aggs.total.value, 1))%)" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Tests Complete!" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
