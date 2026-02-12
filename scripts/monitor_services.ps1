# Robust Monitor for Onboarding Server and Cloudflare Tunnel
# This script ensures both the intake server and the tunnel stay running all day.

$LogFile = "data/monitoring.log"
$WorkDir = Get-Location
$ServerScript = "scripts/onboarding_server.py"
$VenvPython = "$WorkDir\.venv\Scripts\python.exe"

function Write-Log($Message) {
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] $Message"
    Write-Host $LogEntry -ForegroundColor Cyan
    if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" -Force }
    $LogEntry | Out-File -FilePath $LogFile -Append
}

Write-Log "Starting Monitor Service..."

while ($true) {
    # 1. Check Onboarding Server
    $ServerProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*onboarding_server.py*" }
    if (-not $ServerProcess) {
        Write-Log "Onboarding Server NOT found. Restarting..."
        Start-Process $VenvPython -ArgumentList "$ServerScript" -WorkingDirectory $WorkDir -WindowStyle Hidden
    }

    # 1.5. Check Watchdog Service
    $WatchdogProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*watch_onboarding.py*" }
    if (-not $WatchdogProcess) {
        Write-Log "Watchdog Service NOT found. Restarting..."
        Start-Process $VenvPython -ArgumentList "scripts/watch_onboarding.py" -WorkingDirectory $WorkDir -WindowStyle Hidden
    }

    # 2. Check Stable Tunnel (Cloudflare)
    $TunnelProcess = Get-Process -Name cloudflared -ErrorAction SilentlyContinue
    if (-not $TunnelProcess) {
        Write-Log "Stable Tunnel (Cloudflare) NOT found. Restarting..."
        Start-Process pwsh -ArgumentList "-File", "$WorkDir\scripts/start_stable_tunnel.ps1" -WorkingDirectory $WorkDir -WindowStyle Hidden
        Start-Sleep -Seconds 10 # Wait for tunnel to initialize
    }

    # 3. Update GitHub Pages Redirect (Dynamic Redirection)
    try {
        if (Test-Path "data/tunnel.log") {
            $TunnelLog = Get-Content "data/tunnel.log" -Tail 200
            $AllMatches = $TunnelLog | Select-String -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -AllMatches
            if ($AllMatches) {
                $CurrentUrl = $AllMatches[-1].Matches.Value
                $TargetFiles = @("docs/index.md", "docs/index.html", "docs/onboard.html", "index.html", "onboard.html")
                $FilesChanged = 0
                
                foreach ($TargetFile in $TargetFiles) {
                    if (Test-Path $TargetFile) {
                        $Content = Get-Content $TargetFile -Raw
                        if ($Content -match '(var|const) destination = "([^"]+)";') {
                            $StoredUrl = $matches[2]
                            if ($StoredUrl -ne $CurrentUrl) {
                                Write-Log "Tunnel URL changed to $CurrentUrl. Updating $TargetFile..."
                                $NewContent = $Content -replace '(var|const) destination = "[^"]+";', "$($matches[1]) destination = `"$CurrentUrl`";"
                                Set-Content -Path $TargetFile -Value $NewContent
                                if (Get-Command git -ErrorAction SilentlyContinue) {
                                    git add $TargetFile
                                    $FilesChanged++
                                }
                            }
                        }
                    }
                }

                if ($FilesChanged -gt 0) {
                    Write-Log "Committing $FilesChanged update(s) to GitHub..."
                    git commit -m "Auto-update tunnel URL in $FilesChanged file(s)"
                    git push
                    Write-Log "GitHub Pages updated successfully."
                }
            }
        }
    }
    catch {
        Write-Log "Error updating redirection: $_"
    }

    # 4. Verify Public URL Availability
    try {
        # Get Current URL from index.html if not already known from step 3
        if (-not $CurrentUrl -and (Test-Path "index.html")) {
            $IndexContent = Get-Content "index.html" -Raw
            if ($IndexContent -match 'destination = "([^"]+)";') {
                $CurrentUrl = $Matches[1]
            }
        }

        if ($CurrentUrl) {
            # Verify the actual onboarding page content
            $CheckUrl = "$CurrentUrl/onboard"
            $Response = Invoke-WebRequest -Uri $CheckUrl -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
            
            if ($Response.StatusCode -eq 200 -and $Response.Content -match "Gaza Resilience Portal") {
                Write-Log "Public URL Verification SUCCESS: Onboarding page is ACTIVE at $CheckUrl"
            } else {
                Write-Log "Public URL Verification FAIL: $CheckUrl returned status $($Response.StatusCode) or invalid content."
                Write-Log "Restarting Tunnel due to unhealthy response..."
                Stop-Process -Name cloudflared -Force -ErrorAction SilentlyContinue
            }
        }
    }
    catch {
        Write-Log "Public URL Verification ERROR: Could not reach $CurrentUrl. $_"
        Write-Log "Restarting Tunnel due to connectivity failure..."
        Stop-Process -Name cloudflared -Force -ErrorAction SilentlyContinue
    }

    # Wait for 60 seconds before next check
    Start-Sleep -Seconds 60
}
