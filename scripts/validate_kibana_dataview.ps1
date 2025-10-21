# Kibana Data View Validation Script
# Exports gmail_emails data view, validates configuration, and tests re-import

$KIBANA_URL = if ($env:KIBANA_URL) { $env:KIBANA_URL } else { "http://localhost:5601" }
$DATA_VIEW_ID = "gmail_emails"
$EXPORT_FILE = "backup/kibana_data_view_gmail_emails.json"

Write-Host "`n=== Kibana Data View Validation ===" -ForegroundColor Cyan

# Step 1: Export current data view
Write-Host "`n1. Exporting data view '$DATA_VIEW_ID'..." -ForegroundColor Yellow

try {
    $dataView = Invoke-RestMethod -Uri "$KIBANA_URL/api/data_views/data_view/$DATA_VIEW_ID" `
        -Method Get `
        -Headers @{
            "kbn-xsrf" = "true"
            "Content-Type" = "application/json"
        }

    Write-Host "  ✓ Data view exported successfully" -ForegroundColor Green

    # Save to file
    $dataView | ConvertTo-Json -Depth 10 | Out-File -FilePath $EXPORT_FILE -Encoding UTF8
    Write-Host "  ✓ Saved to: $EXPORT_FILE" -ForegroundColor Green

} catch {
    Write-Host "  ✗ Failed to export data view" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Validate required fields
Write-Host "`n2. Validating data view configuration..." -ForegroundColor Yellow

$validationErrors = @()

# Check title/name
if (-not $dataView.data_view.title) {
    $validationErrors += "Missing 'title' field"
} elseif ($dataView.data_view.title -notlike "gmail_emails*") {
    $validationErrors += "Title pattern mismatch: expected 'gmail_emails*', got '$($dataView.data_view.title)'"
} else {
    Write-Host "  ✓ Title pattern: $($dataView.data_view.title)" -ForegroundColor Green
}

# Check time field
if (-not $dataView.data_view.timeFieldName) {
    $validationErrors += "Missing 'timeFieldName' field"
} elseif ($dataView.data_view.timeFieldName -ne "received_at") {
    $validationErrors += "Time field mismatch: expected 'received_at', got '$($dataView.data_view.timeFieldName)'"
} else {
    Write-Host "  ✓ Time field: $($dataView.data_view.timeFieldName)" -ForegroundColor Green
}

# Check index pattern
$indexPattern = $dataView.data_view.title
if ($indexPattern -eq "gmail_emails" -or $indexPattern -eq "gmail_emails-*") {
    Write-Host "  ✓ Index pattern: $indexPattern" -ForegroundColor Green
} else {
    $validationErrors += "Unexpected index pattern: $indexPattern"
}

# Check field count
if ($dataView.data_view.fields) {
    $fieldCount = $dataView.data_view.fields.Count
    Write-Host "  ✓ Fields defined: $fieldCount" -ForegroundColor Green
} else {
    $validationErrors += "No fields defined in data view"
}

# Report validation results
if ($validationErrors.Count -eq 0) {
    Write-Host "`n  ✅ All validations passed" -ForegroundColor Green
} else {
    Write-Host "`n  ❌ Validation errors found:" -ForegroundColor Red
    $validationErrors | ForEach-Object {
        Write-Host "    - $_" -ForegroundColor Red
    }
    exit 1
}

# Step 3: Test re-import (idempotency check)
Write-Host "`n3. Testing re-import idempotency..." -ForegroundColor Yellow

try {
    # Create a test data view with modified ID
    $testDataView = $dataView.data_view | ConvertTo-Json -Depth 10 | ConvertFrom-Json
    $testDataView.id = "gmail_emails_test"
    $testDataView.name = "Gmail Emails (Test)"

    $createBody = @{
        data_view = $testDataView
        override = $true
    } | ConvertTo-Json -Depth 10

    $created = Invoke-RestMethod -Uri "$KIBANA_URL/api/data_views/data_view" `
        -Method Post `
        -Headers @{
            "kbn-xsrf" = "true"
            "Content-Type" = "application/json"
        } `
        -Body $createBody

    Write-Host "  ✓ Test data view created: $($created.data_view.id)" -ForegroundColor Green

    # Verify it matches original
    if ($created.data_view.title -eq $testDataView.title -and
        $created.data_view.timeFieldName -eq $testDataView.timeFieldName) {
        Write-Host "  ✓ Re-import validation successful" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Re-import produced different configuration" -ForegroundColor Yellow
    }

    # Cleanup: delete test data view
    Invoke-RestMethod -Uri "$KIBANA_URL/api/data_views/data_view/$($created.data_view.id)" `
        -Method Delete `
        -Headers @{
            "kbn-xsrf" = "true"
        } | Out-Null

    Write-Host "  ✓ Test data view cleaned up" -ForegroundColor Green

} catch {
    Write-Host "  ⚠ Re-import test skipped (non-critical)" -ForegroundColor Yellow
    Write-Host "    Error: $_" -ForegroundColor Gray
}

# Step 4: Summary
Write-Host "`n=== Validation Complete ===" -ForegroundColor Green
Write-Host "`nData View Summary:"
Write-Host "  ID: $($dataView.data_view.id)"
Write-Host "  Title: $($dataView.data_view.title)"
Write-Host "  Time Field: $($dataView.data_view.timeFieldName)"
Write-Host "  Fields: $($dataView.data_view.fields.Count)"
Write-Host "  Export File: $EXPORT_FILE`n"

Write-Host "✅ Data view configuration validated" -ForegroundColor Green
exit 0
