param(
  [string]$KbnUrl = 'http://localhost:5601',
  [string]$User = 'elastic',
  [string]$Pass = 'changeme'
)

$pair = "${User}:${Pass}"
$auth = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($pair))

function Import-Ndjson([string]$Path){
  $boundary = [System.Guid]::NewGuid().ToString()
  $filePath = Resolve-Path $Path
  $fileName = Split-Path $filePath -Leaf
  $fileBytes = [System.IO.File]::ReadAllBytes($filePath)
  
  $bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: application/x-ndjson",
    "",
    [System.Text.Encoding]::UTF8.GetString($fileBytes),
    "--$boundary--"
  )
  
  $body = $bodyLines -join "`r`n"
  
  try {
    $response = Invoke-WebRequest -Method Post -Uri "$KbnUrl/kibana/api/saved_objects/_import?createNewCopies=true" `
      -Headers @{ 
        'kbn-xsrf' = 'true'
        'Authorization' = "Basic $auth"
      } `
      -ContentType "multipart/form-data; boundary=$boundary" `
      -Body $body
    
    Write-Host "✅ Imported: $fileName" -ForegroundColor Green
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
  } catch {
    Write-Host "❌ Failed to import: $fileName" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
  }
}

Write-Host "`n📊 Importing Kibana Saved Objects..." -ForegroundColor Cyan
Write-Host "Kibana URL: $KbnUrl" -ForegroundColor Gray
Write-Host "User: $User`n" -ForegroundColor Gray

Import-Ndjson 'infra\kibana\emails_index_pattern.ndjson'
Import-Ndjson 'infra\kibana\emails_saved_search.ndjson'

Write-Host "`n✅ Import complete!" -ForegroundColor Green
