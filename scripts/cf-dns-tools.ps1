<#
.SYNOPSIS
  Cloudflare DNS helper: get Zone ID, list DNS records, and toggle proxy.

.DESCRIPTION
  Helper functions to interact with Cloudflare API for DNS management.
  Requires: CF_API_TOKEN environment variable with Zone:Read and DNS:Edit permissions.

.EXAMPLE
  $env:CF_API_TOKEN = "your_token_here"
  . .\cf-dns-tools.ps1
  Get-CFZone -Domain "applylens.app"
  Get-CFDnsRecord -ZoneId "<ZONE_ID>" -Name "applylens.app"
  Toggle-CFProxy -Domain "applylens.app" -RecordName "applylens.app" -Proxied:$false
  Toggle-CFProxy -Domain "applylens.app" -RecordName "applylens.app" -Proxied:$true
#>

function _CFHeaders {
  if (-not $env:CF_API_TOKEN) { throw "Set `$env:CF_API_TOKEN first." }
  return @{ "Authorization" = "Bearer $($env:CF_API_TOKEN)"; "Content-Type" = "application/json" }
}

function Get-CFZone {
  param([Parameter(Mandatory)][string]$Domain)
  $url = "https://api.cloudflare.com/client/v4/zones?name=$Domain"
  $resp = Invoke-RestMethod -Headers (_CFHeaders) -Uri $url -Method GET
  if (-not $resp.success -or $resp.result.Count -eq 0) {
    throw "Zone not found for $Domain"
  }
  $zone = $resp.result[0]
  [PSCustomObject]@{
    id          = $zone.id
    name        = $zone.name
    status      = $zone.status
    plan        = $zone.plan.name
    name_servers= ($zone.name_servers -join ", ")
  }
}

function Get-CFDnsRecords {
  param(
    [Parameter(Mandatory)][string]$ZoneId,
    [string]$Type,                # A, AAAA, CNAME, etc.
    [string]$Name                 # FQDN filter (e.g., "applylens.app" or "www.applylens.app")
  )
  $qs = @()
  if ($Type) { $qs += "type=$Type" }
  if ($Name) { $qs += "name=$Name" }
  $q = ($qs -join "&")
  $url = "https://api.cloudflare.com/client/v4/zones/$ZoneId/dns_records" + ($(if($q){"?$q"}else{""}))
  $resp = Invoke-RestMethod -Headers (_CFHeaders) -Uri $url -Method GET
  $resp.result | Select-Object id,type,name,content,proxied,ttl
}

function Get-CFDnsRecord {
  param(
    [Parameter(Mandatory)][string]$ZoneId,
    [Parameter(Mandatory)][string]$Name
  )
  $rec = Get-CFDnsRecords -ZoneId $ZoneId -Name $Name | Select-Object -First 1
  if (-not $rec) { throw "Record not found: $Name" }
  return $rec
}

function Toggle-CFProxy {
  param(
    [Parameter(Mandatory)][string]$Domain,       # e.g., applylens.app
    [Parameter(Mandatory)][string]$RecordName,   # e.g., applylens.app or www.applylens.app
    [Parameter(Mandatory)][bool]$Proxied         # $true (orange) / $false (gray)
  )
  $zone = Get-CFZone -Domain $Domain
  $rec  = Get-CFDnsRecord -ZoneId $zone.id -Name $RecordName

  $body = @{ proxied = $Proxied } | ConvertTo-Json
  $url  = "https://api.cloudflare.com/client/v4/zones/$($zone.id)/dns_records/$($rec.id)"
  $resp = Invoke-RestMethod -Headers (_CFHeaders) -Uri $url -Method PATCH -Body $body

  [PSCustomObject]@{
    zone_name   = $zone.name
    zone_id     = $zone.id
    record_id   = $rec.id
    record_name = $rec.name
    type        = $rec.type
    new_proxied = $resp.result.proxied
    content     = $resp.result.content
  }
}

function CF-PrintIds {
  param([Parameter(Mandatory)][string]$Domain)
  $zone = Get-CFZone -Domain $Domain
  Write-Host "Zone:" $zone.name "→" $zone.id -ForegroundColor Cyan
  $recs = Get-CFDnsRecords -ZoneId $zone.id
  $recs | ForEach-Object {
    $proxiedColor = if($_.proxied){"Green"}else{"Yellow"}
    Write-Host ("{0,-30} {1,-6} proxied={2,-5} id={3}" -f $_.name, $_.type, $_.proxied, $_.id) -ForegroundColor $proxiedColor
  }
}

# Export functions
Export-ModuleMember -Function Get-CFZone, Get-CFDnsRecords, Get-CFDnsRecord, Toggle-CFProxy, CF-PrintIds
