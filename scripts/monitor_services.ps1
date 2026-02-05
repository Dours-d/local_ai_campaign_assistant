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
    $ServerProcess = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%onboarding_server.py%'"
    if (-not $ServerProcess) {
        Write-Log "Onboarding Server NOT found. Restarting..."
        Start-Process $VenvPython -ArgumentList "$ServerScript" -WorkingDirectory $WorkDir -WindowStyle Hidden
    }

    # 2. Check Stable Tunnel (Cloudflare)
    $TunnelProcess = Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'"
    if (-not $TunnelProcess) {
        Write-Log "Stable Tunnel (Cloudflare) NOT found. Restarting..."
        Start-Process pwsh -ArgumentList "-File", "$WorkDir\scripts/start_stable_tunnel.ps1" -WorkingDirectory $WorkDir -WindowStyle Hidden
        Start-Sleep -Seconds 10 # Wait for tunnel to initialize
    }

    # 3. Update GitHub Pages Redirect (Dynamic Redirection)
    try {
        if (Test-Path "data/tunnel.log") {
            $TunnelLog = Get-Content "data/tunnel.log" -Tail 100 | Out-String
            if ($TunnelLog -match "https://[a-z0-9-]+\.trycloudflare\.com") {
                $CurrentUrl = $matches[0]
                $CurrentUrl = $matches[0]
                $TargetFile = "docs/index.md"
                
                if (Test-Path $TargetFile) {
                    $Content = Get-Content $TargetFile -Raw
                    # Regex to find the javascript variable definition
                    if ($Content -match 'var destination = "([^"]+)";') {
                        $StoredUrl = $matches[1]
                         
                        if ($StoredUrl -ne $CurrentUrl) {
                            Write-Log "Tunnel URL changed to $CurrentUrl. Updating $TargetFile..."
                            $NewContent = $Content -replace 'var destination = "[^"]+";', "var destination = `"$CurrentUrl`";"
                            Set-Content -Path $TargetFile -Value $NewContent
                             
                            # Git Automation
                            if (Get-Command git -ErrorAction SilentlyContinue) {
                                Write-Log "Committing direct link update to GitHub..."
                                git add $TargetFile
                                # Remove data file if it exists, as we are deprecated it to avoid confusion
                                if (Test-Path "docs/_data/tunnel.yml") { git rm "docs/_data/tunnel.yml" -ErrorAction SilentlyContinue }
                                
                                git commit -m "Auto-update tunnel URL in index.md"
                                git push
                                Write-Log "GitHub Pages updated successfully."
                            }
                            else {
                                Write-Log "WARNING: git command not found. Cannot update portal redirect."
                            }
                        }
                    }
                }
            }
        }
    }
    catch {
        Write-Log "Error updating redirection: $_"
    }

    # Wait for 60 seconds before next check
    Start-Sleep -Seconds 60
}
