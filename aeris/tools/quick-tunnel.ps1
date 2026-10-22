# AERIS on a Cloudflare quick tunnel, for TESTING ONLY (test data, this laptop).
# Starts (or restarts) the tunnel, points AERIS at the new https://<random>.trycloudflare.com address,
# restarts the app and prints the link to share. The address changes every time this runs.
# Uses HTTP/2 over TCP: steadier than the default QUIC (UDP) on office Wi-Fi.
#   powershell -ExecutionPolicy Bypass -File aeris\tools\quick-tunnel.ps1
$ErrorActionPreference = "Stop"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$log = Join-Path $env:USERPROFILE ".cloudflared\aeris-quick-tunnel.log"
$dockerDir = Join-Path $PSScriptRoot "..\docker"
$envFile = Join-Path $dockerDir ".env"
# random names are made of English words: skip ones that read badly in a health-emergency setting
$avoid = 'terror|kill|dead|death|bomb|war|gun|virus|ebola|sex|drug|attack|weapon|crash|blood|hate|steal|crime|fail'

New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
$url = $null
for ($try = 1; $try -le 5 -and -not $url; $try++) {
    Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 2
    if (Test-Path $log) { Remove-Item $log }
    Start-Process -FilePath $cloudflared -WindowStyle Hidden `
        -ArgumentList @("tunnel", "--no-autoupdate", "--protocol", "http2", "--url", "http://localhost:8080", "--logfile", $log)
    for ($i = 0; $i -lt 30 -and -not $url; $i++) {
        Start-Sleep 2
        if (Test-Path $log) {
            $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
            if ($m) { $url = $m.Matches[0].Value }
        }
    }
    if ($url -and $url -match $avoid) { Write-Host "skipping $url"; $url = $null }
}
if (-not $url) { throw "No tunnel address; see $log" }

# AERIS must know its public address and that it sits behind https
$lines = @()
if (Test-Path $envFile) { $lines = Get-Content $envFile | Where-Object { $_ -notmatch '^(GRAILS_SERVER_URL|SERVER_USE_FORWARD_HEADERS)=' } }
$lines += "GRAILS_SERVER_URL=$url/openboxes/"
$lines += "SERVER_USE_FORWARD_HEADERS=true"
Set-Content -Path $envFile -Value $lines -Encoding ascii
Push-Location $dockerDir
docker compose up -d --no-build app
Pop-Location

Write-Host "Waiting for AERIS..."
for ($i = 0; $i -lt 60; $i++) {
    try { if ((Invoke-WebRequest -UseBasicParsing "http://localhost:8080/openboxes/auth/login" -TimeoutSec 5).StatusCode -eq 200) { break } } catch { }
    Start-Sleep 5
}
Write-Host ""
Write-Host "AERIS (test) is at: $url/openboxes" -ForegroundColor Green
