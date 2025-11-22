<#
.SYNOPSIS
  Inspect Cloudflare rules for a domain (Page Rules, Cache Rules, Transform Rules, Rulesets).
  Highlights any rule expressions referencing /health.

.USAGE
  $env:CF_API_TOKEN = "<YOUR_TOKEN>"
  . .\scripts\cf-rules-inspect.ps1
  Inspect-CFRules -Domain "applylens.app"

.OUTPUT
  Prints summaries and a final "Possible /health matches" section.
#>

function _CFHeaders {
  if (-not $env:CF_API_TOKEN) { throw "Set `$env:CF_API_TOKEN first." }
  return @{ "Authorization" = "Bearer $($env:CF_API_TOKEN)"; "Content-Type" = "application/json" }
}

function Get-CFZone {
  param([Parameter(Mandatory)][string]$Domain)
  $u = "https://api.cloudflare.com/client/v4/zones?name=$Domain"
  $r = Invoke-RestMethod -Headers (_CFHeaders) -Uri $u -Method GET
  if (-not $r.success -or $r.result.Count -eq 0) { throw "Zone not found for $Domain" }
  $r.result[0]
}

function Get-CFPageRules {
  param([Parameter(Mandatory)][string]$ZoneId)
  $u = "https://api.cloudflare.com/client/v4/zones/$ZoneId/pagerules"
  (Invoke-RestMethod -Headers (_CFHeaders) -Uri $u -Method GET).result
}

# Rulesets API helpers (Cache Rules, Transform Rules, Configuration Rules, etc.)
function Get-CFRulesets {
  param([Parameter(Mandatory)][string]$ZoneId)
  $u = "https://api.cloudflare.com/client/v4/zones/$ZoneId/rulesets"
  (Invoke-RestMethod -Headers (_CFHeaders) -Uri $u -Method GET).result
}

function Get-CFPhaseEntrypoint {
  param(
    [Parameter(Mandatory)][string]$ZoneId,
    [Parameter(Mandatory)][string]$Phase # e.g., http_request_cache_settings
  )
  $u = "https://api.cloudflare.com/client/v4/zones/$ZoneId/rulesets/phases/$Phase/entrypoint"
  try {
    (Invoke-RestMethod -Headers (_CFHeaders) -Uri $u -Method GET).result
  } catch {
    $null
  }
}

# Common HTTP rule phases you likely care about
$CF_RULE_PHASES = @(
  "http_request_cache_settings",       # Cache Rules
  "http_response_headers_transform",   # Response header mods
  "http_request_transform",            # URI / method / header transforms
  "http_request_late_transform",       # Late transforms (after WAF)
  "http_request_dynamic_redirect",     # Redirect rules
  "http_ratelimit",                    # Rate-limiting
  "http_request_firewall_custom"       # Custom WAF rules
)

function _PrintHeadline($text) {
  Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Inspect-CFRules {
  param([Parameter(Mandatory)][string]$Domain)

  $zone = Get-CFZone -Domain $Domain
  $zoneId = $zone.id
  _PrintHeadline "Zone"
  "{0}  (id: {1})  status={2}  plan={3}" -f $zone.name, $zone.id, $zone.status, $zone.plan.name

  # 1) Page Rules (legacy but still widely used)
  _PrintHeadline "Page Rules"
  $pageRules = Get-CFPageRules -ZoneId $zoneId
  if (-not $pageRules -or $pageRules.Count -eq 0) {
    Write-Host "(none)"
  } else {
    $pageRules | ForEach-Object {
      $targets = ($_.targets | ForEach-Object { $_.constraint.value }) -join ", "
      $actions = ($_.actions | ForEach-Object { if ($_.id) { $_.id } else { $_.id } }) -join ", "
      "{0,-32}  targets={1}  status={2}  actions={3}" -f $_.id, $targets, $_.status, $actions
    }
  }

  # 2) Rulesets (modern rules, this is where Cache Rules/Transform live)
  _PrintHeadline "Rulesets (all)"
  $allRulesets = Get-CFRulesets -ZoneId $zoneId
  if ($allRulesets) {
    $allRulesets | ForEach-Object {
      "{0}  phase={1,-30}  kind={2,-10}  version={3}  (id: {4})" -f $_.name, $_.phase, $_.kind, $_.version, $_.id
    }
  } else {
    Write-Host "(none)"
  }

  # 3) Entrypoints per phase (to see concrete rule expressions/actions)
  $healthHits = New-Object System.Collections.Generic.List[object]
  foreach ($phase in $CF_RULE_PHASES) {
    _PrintHeadline "Phase entrypoint: $phase"
    $ep = Get-CFPhaseEntrypoint -ZoneId $zoneId -Phase $phase
    if (-not $ep) { Write-Host "(none)"; continue }

    # Entry point is itself a ruleset with .rules
    if ($ep.rules) {
      $idx = 0
      foreach ($rule in $ep.rules) {
        $idx++
        $expr   = $rule.expression
        $action = $rule.action
        $enabled= $rule.enabled
        $name   = if ($rule.name) { $rule.name } else { "rule-$idx" }

        # Print concise summary
        "{0}  enabled={1,-5}  action={2,-28} expr={3}" -f $name, $enabled, $action, ($expr -replace '\s+',' ')

        # Collect any likely-health matches for spotlighting
        if ($expr -match '/health') {
          $healthHits.Add([PSCustomObject]@{
            phase=$phase; name=$name; action=$action; enabled=$enabled; expr=$expr
          }) | Out-Null
        }

        # Some actions (e.g., set_cache_settings / set_static_route / set_header) carry parameters:
        if ($rule.parameters) {
          $p = $rule.parameters | ConvertTo-Json -Depth 6
          "  └─ params: $p" | Write-Host
        }
      }
    } else {
      Write-Host "(no rules)"
    }
  }

  # 4) Spotlight: Anything touching /health
  _PrintHeadline "Possible /health matches"
  if ($healthHits.Count -gt 0) {
    $healthHits | ForEach-Object {
      "[{0}] {1}  enabled={2}  action={3}`n  expr: {4}" -f $_.phase, $_.name, $_.enabled, $_.action, $_.expr
    }
  } else {
    Write-Host "(no rules referencing /health)"
  }

  Write-Host "`nTip: If a Cache Rule sets cacheability, add an explicit bypass rule for /health or adjust that rule's filter to exclude it." -ForegroundColor Yellow
}
