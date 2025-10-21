param(
  [Parameter(Mandatory=$true)][string]$EmailsLensId,
  [Parameter(Mandatory=$true)][string]$TrafficLensId
)
$in = 'infra/kibana/dashboard_applylens.ndjson'
$out = 'infra/kibana/dashboard_applylens.patched.ndjson'

# Build panels JSON
$panels = @'
[
  {"version":"8","type":"lens","gridData":{"x":0,"y":0,"w":24,"h":16,"i":"1"},"panelIndex":"1","embeddableConfig":{},"panelRefName":"panel_0"},
  {"version":"8","type":"lens","gridData":{"x":0,"y":16,"w":24,"h":12,"i":"2"},"panelIndex":"2","embeddableConfig":{},"panelRefName":"panel_1"}
]
'@

$dash = Get-Content $in -Raw | ConvertFrom-Json
$dash.attributes.panelsJSON = $panels

# Build references
$refs = @(
  @{type='lens'; name='panel_0'; id=$EmailsLensId},
  @{type='lens'; name='panel_1'; id=$TrafficLensId}
)
$dash | Add-Member -NotePropertyName 'references' -NotePropertyValue $refs -Force

# Write as single-line NDJSON
$dash | ConvertTo-Json -Depth 10 -Compress | Set-Content -Path $out -NoNewline
Write-Host "Patched dashboard → $out"
