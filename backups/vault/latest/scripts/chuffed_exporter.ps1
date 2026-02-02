
# Chuffed Comprehensive Report Exporter
# Version: 1.6 (Persistent Discovery & Robust Scraper)

param(
    [string]$Port = "9222",
    [string]$OutputDir = "data/reports/chuffed"
)

if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir -Force }

# 1. Connect to CDP
$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$ChTab = $Tabs | Where-Object { $_.url -match "chuffed.org" -and $_.type -eq "page" } | Select-Object -First 1

if (-not $ChTab) { 
    Write-Host "No Chuffed tab found. Open Chrome with Chuffed dashboard: https://chuffed.org/dashboard/reports/per-campaign" -ForegroundColor Red; exit 
}

$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
$ws.ConnectAsync([Uri]$ChTab.webSocketDebuggerUrl, $cts.Token).Wait()

function Send-CDP {
    param([string]$expr)
    $msg = @{ id = Get-Random; method = "Runtime.evaluate"; params = @{ expression = $expr; returnByValue = $true; awaitPromise = $true } } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    $buf = [byte[]]::new(20MB) 
    $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $res.Wait()
    $resp = [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
    if ($resp.result.exceptionDetails) { Write-Host "JS Error: $($resp.result.exceptionDetails.exception.description)" -ForegroundColor Red }
    return $resp
}

Write-Host "`n=== Chuffed Automated Exporter v1.7 [TURBO] ===" -ForegroundColor Cyan

# 2. Fast Discovery
Write-Host "Discovered campaigns (Target: ~277)..."
$getCampaignsJs = @'
(async function() {
    const campaigns = new Map();
    const scroller = document.querySelector('.main') || document.documentElement;
    
    // Fast scroll loop
    for (let i = 0; i < 30; i++) {
        document.querySelectorAll('.dashboard-card').forEach(card => {
            const titleEl = card.querySelector('.dashboard-card__heading-link');
            const link = card.querySelector('a[href*="/dashboard/reports/"]');
            if (link) {
                const id = link.href.match(/\/(\d+)(?:\?|$)/)?.[1] || link.href.split('/').pop();
                if (!campaigns.has(id)) {
                    campaigns.set(id, { id: id, title: titleEl ? titleEl.innerText.trim() : "Unknown", url: link.href });
                }
            }
        });
        window.scrollTo(0, document.body.scrollHeight);
        scroller.scrollTo(0, scroller.scrollHeight);
        const loadMore = Array.from(document.querySelectorAll('button, a')).find(el => (el.innerText || "").toLowerCase().includes('load more'));
        if (loadMore) loadMore.click();
        await new Promise(r => setTimeout(r, 800));
        if (campaigns.size >= 277) break; 
    }
    return Array.from(campaigns.values());
})()
'@

$resp = Send-CDP $getCampaignsJs
$campaigns = $resp.result.result.value
Write-Host "Discovered $($campaigns.Count) campaigns."

# 3. Parallel Background Scraping
$BatchSize = 5
for ($i = 0; $i -lt $campaigns.Count; $i += $BatchSize) {
    $batch = $campaigns | Select-Object -Skip $i -First $BatchSize
    Write-Host "Processing batch $($i/$BatchSize + 1) ($($i+1) to $($i+$batch.Count))..." -ForegroundColor Yellow
    
    $batchJs = @"
    (async function() {
        const results = [];
        const targets = $($batch | ConvertTo-Json -Compress);
        
        for (const c of targets) {
            try {
                // Fetch the report page HTML in the background
                const res = await fetch(c.url);
                const html = await res.text();
                const doc = new DOMParser().parseFromString(html, 'text/html');
                
                // Extract table data from the fetched HTML
                const table = doc.querySelector('table');
                if (!table) {
                    results.push({ id: c.id, error: "No table in background fetch" });
                    continue;
                }
                
                const rows = Array.from(table.querySelectorAll('tr'));
                const headers = Array.from(rows[0].querySelectorAll('th, td')).map(el => el.innerText.trim());
                const donations = rows.slice(1).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    const obj = {};
                    headers.forEach((h, i) => { if(cells[i]) obj[h] = cells[i].innerText.trim(); });
                    return obj;
                });
                results.push({ id: c.id, donations: donations });
            } catch (e) {
                results.push({ id: c.id, error: e.message });
            }
        }
        return results;
    })()
"@

    $br = Send-CDP $batchJs
    $batchRes = $br.result.result.value
    
    foreach ($res in $batchRes) {
        if ($res.donations) {
            $outputPath = Join-Path $OutputDir "$($res.id).json"
            $res | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputPath -Encoding utf8
            Write-Host "  ✅ $($res.id) saved ($($res.donations.Count) donations)" -ForegroundColor Green
        }
        else {
            Write-Warning "  ❌ $($res.id) failed: $($res.error)"
        }
    }
}

Write-Host "`n=== [TURBO COMPLETE] ===" -ForegroundColor Cyan
