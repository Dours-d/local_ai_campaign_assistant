
# Chuffed Comprehensive Report Exporter
# Version: 6.0 (Direct API)

param(
    [string]$Port = "9222",
    [string]$OutputDir = "data/reports/chuffed"
)

# 1. Setup Directories
$scriptPath = Split-Path $PSCommandPath -Parent
$root = Split-Path $scriptPath -Parent
$outDir = Join-Path $root $OutputDir
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$outAbs = (Get-Item $outDir).FullName
$defaultDownloads = Join-Path $env:USERPROFILE "Downloads"

# 2. Load Hardwired IDs
$jsonPath = Join-Path $root "data/chuffed_campaigns.json"
if (-not (Test-Path $jsonPath)) { Write-Host "Source file not found at $jsonPath. Exit." -ForegroundColor Red; exit }
$rawJson = Get-Content $jsonPath -Raw
$staticList = $rawJson | ConvertFrom-Json
Write-Host "Loaded $($staticList.Count) campaigns" -ForegroundColor Cyan

# 3. Connect to CDP
$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$ChTab = $Tabs | Where-Object { $_.url -match "chuffed.org" -and $_.type -eq "page" } | Select-Object -First 1

if (-not $ChTab) { 
    Write-Host "No Chuffed tab found. Open Chrome with Chuffed dashboard." -ForegroundColor Red; exit 
}

$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
$ws.ConnectAsync([Uri]$ChTab.webSocketDebuggerUrl, $cts.Token).Wait()

function Send-CDP {
    param([string]$method = "Runtime.evaluate", [hashtable]$params)
    if ($null -eq $params -and ($method -match "\s" -or $method -match "\(")) {
        $params = @{ expression = $method; returnByValue = $true; awaitPromise = $true }
        $method = "Runtime.evaluate"
    }
    $msg = @{ id = Get-Random; method = $method; params = $params } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    
    $allBytes = New-Object System.Collections.Generic.List[byte]
    $buffer = [byte[]]::new(65536)
    do {
        $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cts.Token).Result
        if ($res.Count -gt 0) {
            $slice = [byte[]]$buffer[0..($res.Count - 1)]
            $allBytes.AddRange($slice)
        }
    } while (-not $res.EndOfMessage)
    
    return [System.Text.Encoding]::UTF8.GetString($allBytes.ToArray()) | ConvertFrom-Json
}

Write-Host "`n=== Chuffed Automated Exporter v6.0 [DIRECT API] ===" -ForegroundColor Cyan

# 4. Processing Loop - Call API directly for each campaign
$count = 0
foreach ($c in $staticList) {
    $count++
    $targetFile = Join-Path $outAbs "$($c.id).csv"
    if (Test-Path $targetFile) { 
        Write-Host "[$count/$($staticList.Count)] ⏩ Skip $($c.id)" -ForegroundColor Gray
        continue 
    }

    Write-Host "[$count/$($staticList.Count)] Fetching: $($c.id)..." -ForegroundColor Yellow
    
    # Pre-Sniper Cleanup
    Get-ChildItem -Path $defaultDownloads -Filter "chuffed_donor_*.csv" | Remove-Item -Force -ErrorAction SilentlyContinue

    # Snapshot Downloads folder
    $filesBefore = Get-ChildItem -Path $defaultDownloads -Filter "chuffed*" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    
    # Direct API call via JavaScript
    $apiJs = @"
    (async function() {
        try {
            const url = 'https://chuffed.org/api/v3/reports/campaigns/$($c.id)/donor?format=csv&acknowledged=true';
            
            // Create a hidden link and trigger download
            const link = document.createElement('a');
            link.href = url;
            link.download = 'chuffed_donor_$($c.id).csv';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            return { status: "TRIGGERED", id: $($c.id) };
        } catch (e) {
            return { status: "ERROR", error: e.message };
        }
    })()
"@
    $res = Send-CDP $apiJs
    $result = $res.result.result.value
    
    if ($result.status -eq "ERROR") {
        Write-Warning "  ❌ API Error: $($result.error)"
        continue
    }
    
    Write-Host "  API triggered" -ForegroundColor Gray

    # Monitor Downloads folder for new file
    $found = $false
    for ($i = 0; $i -lt 20; $i++) {
        $dlFiles = Get-ChildItem -Path $defaultDownloads -Filter "chuffed_donor_*.csv" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
        $newDlFiles = $dlFiles | Where-Object { $filesBefore -notcontains $_ }
        
        if ($newDlFiles) {
            foreach ($nf in $newDlFiles) {
                if ($nf -notmatch '\.(crdownload|tmp)$') {
                    Start-Sleep -Milliseconds 1000
                    Move-Item -Path $nf -Destination $targetFile -Force
                    Write-Host "  ✅ Saved: $($c.id).csv" -ForegroundColor Green
                    $found = $true; break
                }
            }
        }
        if ($found) { break }
        Start-Sleep -Milliseconds 500
    }

    if (-not $found) { 
        Write-Warning "  ❌ Download failed (no file appeared)." 
    }
}
Write-Host "`n=== [EXPORT COMPLETE] ===" -ForegroundColor Cyan
