<#
.SYNOPSIS
    WhatsApp Bulk CSV Exporter (Text Density Version)
#>

param (
    [string]$Port = "9222",
    [string]$ExportDir = "data\exports",
    [int]$MaxScrolls = 10
)

function Invoke-CDPCmd {
    param($ws, $method, $params)
    try {
        $msg = @{ id = Get-Random; method = $method; params = $params } | ConvertTo-Json -Compress
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
        $ws.SendAsync([ArraySegment[byte]]::new($bytes), 1, $true, [System.Threading.CancellationToken]::None).Wait()
        $buf = [byte[]]::new(2MB); $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), [System.Threading.CancellationToken]::None); $res.Wait()
        return [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
    }
    catch { return $null }
}

if (-not (Test-Path $ExportDir)) { New-Item -Path $ExportDir -ItemType Directory | Out-Null }

try {
    $Tabs = Invoke-RestMethod "http://localhost:$Port/json"
    $WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" } | Select-Object -First 1
    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, [System.Threading.CancellationToken]::None).Wait()

    Write-Host "Discovering chats via text density..." -ForegroundColor Gray
    $listJs = @"
        (function() {
            let entries = Array.from(document.querySelectorAll('div[role="row"]')).map(el => {
                let text = el.innerText.split('\n')[0];
                return text;
            }).filter(t => t && t.length > 2 && !['Archived','Unread','Groups','Searching'].includes(t));
            return Array.from(new Set(entries));
        })()
"@
    $chats = (Invoke-CDPCmd $ws "Runtime.evaluate" @{expression = $listJs; returnByValue = $true }).result.result.value

    Write-Host "Found $($chats.Count) candidates. Starting Extraction..." -ForegroundColor Green

    foreach ($name in $chats) {
        $raw = $name
        foreach ($bidi in 0x202A..0x202E) { $raw = $raw -replace [char]$bidi, "" }
        $safe = $raw -replace '[^a-zA-Z0-9\s-]', '' -replace '\s+', '_'
        if (-not $safe) { $safe = "Unnamed_" + (Get-Random) }
        $path = Join-Path $ExportDir "$safe.csv"
        if (Test-Path $path) { continue }

        Write-Host ">>> Opening [$name]..." -ForegroundColor Cyan
        $clickJs = @"
            (function(target) {
                let el = Array.from(document.querySelectorAll('div[role="row"]')).find(e => e.innerText.includes(target));
                if (el) { el.click(); return "clicked"; }
                return "not_found";
            })(arguments[0])
"@
        Invoke-CDPCmd $ws "Runtime.evaluate" @{expression = $clickJs; arguments = @(@{value = $name }) } | Out-Null
        Start-Sleep -Seconds 5

        # Agnostic Extraction
        $extractJs = @"
            (function() {
                let items = document.querySelectorAll('.copyable-text, [data-pre-plain-text]');
                let results = [];
                let seen = new Set();
                items.forEach(el => {
                    let b = el.innerText.trim();
                    let m = el.getAttribute('data-pre-plain-text') || '';
                    if (b && !seen.has(b)) {
                        seen.add(b);
                        results.push({ m: m, b: b });
                    }
                });
                return results;
            })()
"@
        $msgs = (Invoke-CDPCmd $ws "Runtime.evaluate" @{expression = $extractJs; returnByValue = $true }).result.result.value
        
        if ($msgs -and $msgs.Count -gt 0) {
            $lines = @("Timestamp,Sender,Message")
            foreach ($m in $msgs) {
                $ts = "Unknown"; $sn = "Unknown"
                if ($m.m -match '\[(.*?)\]\s*(.*)') {
                    $ts = $Matches[1]
                    if ($Matches[2] -match '^(.*?):') { $sn = $Matches[1] }
                }
                $lines += "`"$ts`",`"$sn`",`"$($m.b -replace '[\r\n]+',' ' -replace '"','""')`""
            }
            $lines | Out-File $path -Encoding utf8
            Write-Host "   SUCCESS: Saved $($msgs.Count) items to $safe.csv" -ForegroundColor Green
        }
    }
}
catch { Write-Warning "Error: $_" }
finally { if ($ws) { $ws.Dispose() } }
