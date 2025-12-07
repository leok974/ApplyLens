# Test Contact and Links Auto-fill
# Verifies the profile API returns structured contact/links data

Write-Host "`n🧪 Testing Contact & Links Auto-fill..." -ForegroundColor Cyan

# 1. Get profile
Write-Host "`n1️⃣ Fetching profile from API..." -ForegroundColor Yellow
$profile = Invoke-RestMethod -Uri "http://localhost:8003/api/profile/me"

Write-Host "✅ Profile received" -ForegroundColor Green
Write-Host "   Name: $($profile.name)" -ForegroundColor White
Write-Host "   Headline: $($profile.headline)" -ForegroundColor White

# 2. Verify contact structure
Write-Host "`n2️⃣ Checking contact structure..." -ForegroundColor Yellow
if ($profile.contact) {
    Write-Host "✅ Contact object exists" -ForegroundColor Green
    Write-Host "   Email: $($profile.contact.email)" -ForegroundColor White
    Write-Host "   Phone: $($profile.contact.phone)" -ForegroundColor White
    Write-Host "   City: $($profile.contact.location_city)" -ForegroundColor White
    Write-Host "   Country: $($profile.contact.location_country)" -ForegroundColor White
} else {
    Write-Host "❌ Contact object missing!" -ForegroundColor Red
}

# 3. Verify links structure
Write-Host "`n3️⃣ Checking links structure..." -ForegroundColor Yellow
if ($profile.links) {
    Write-Host "✅ Links object exists" -ForegroundColor Green
    Write-Host "   LinkedIn: $($profile.links.linkedin)" -ForegroundColor White
    Write-Host "   GitHub: $($profile.links.github)" -ForegroundColor White
    Write-Host "   Website: $($profile.links.website)" -ForegroundColor White
    Write-Host "   Portfolio: $($profile.links.portfolio)" -ForegroundColor White
} else {
    Write-Host "❌ Links object missing!" -ForegroundColor Red
}

# 4. Test expected field mappings
Write-Host "`n4️⃣ Testing extension field mappings..." -ForegroundColor Yellow

$fieldMappings = @{
    "email" = $profile.contact.email
    "phone" = $profile.contact.phone
    "location" = "$($profile.contact.location_city), $($profile.contact.location_country)"
    "country" = $profile.contact.location_country
    "linkedin" = $profile.links.linkedin
    "github" = $profile.links.github
    "website" = $profile.links.website
    "first_name" = $profile.name.Split(" ")[0]
    "last_name" = if ($profile.name.Split(" ").Length -gt 1) { $profile.name.Split(" ")[-1] } else { $null }
}

$filledCount = 0
foreach ($field in $fieldMappings.Keys) {
    $value = $fieldMappings[$field]
    if ($value) {
        Write-Host "   ✅ $field`: $value" -ForegroundColor Green
        $filledCount++
    } else {
        Write-Host "   ⚠️  $field`: (empty)" -ForegroundColor Yellow
    }
}

# 5. Summary
Write-Host "`n📊 Summary:" -ForegroundColor Cyan
Write-Host "   Profile fields auto-filled: $filledCount/9" -ForegroundColor White
Write-Host "   Expected in extension: 'Profile: $filledCount' in source summary" -ForegroundColor Gray

if ($filledCount -ge 7) {
    Write-Host "`n✅ Test PASSED! Extension should auto-fill $filledCount fields from profile" -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Test WARNING: Expected at least 7 fields, got $filledCount" -ForegroundColor Yellow
}

Write-Host "`nNext steps:" -ForegroundColor Magenta
Write-Host "  1. Reload extension in Chrome" -ForegroundColor White
Write-Host "  2. Open a job application form" -ForegroundColor White
Write-Host "  3. Click 'Scan Form'" -ForegroundColor White
Write-Host "  4. Check console for: '[v0.3] Initial suggestions built: X fields have values'" -ForegroundColor Gray
Write-Host "  5. Verify source summary shows: 'Profile: $filledCount'" -ForegroundColor Gray
