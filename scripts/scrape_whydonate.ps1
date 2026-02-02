<#
.SYNOPSIS
    Whydonate Dashboard Campaign Scraper
.DESCRIPTION
    Uses Chrome DevTools Protocol to extract campaign data from Whydonate dashboard.
    Requires Chrome running with --remote-debugging-port=9222 and Whydonate dashboard open.
#>

param (
    [string]$Port = "9222",
    [string]$OutputFile = "data\whydonate_full_campaigns.json"
)

function Invoke-CDPCmd {
    param($ws, $method, $params)
    try {
        $id = Get-Random
        $msg = @{ id = $id; method = $method; params = $params } | ConvertTo-Json -Compress -Depth 10
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
        $ws.SendAsync([ArraySegment[byte]]::new($bytes), 1, $true, [System.Threading.CancellationToken]::None).Wait()
        $buf = [byte[]]::new(2MB)
        $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), [System.Threading.CancellationToken]::None)
        $res.Wait()
        return [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
    }
    catch { 
        Write-Warning "CDP Error: $_"
        return $null 
    }
}

try {
    Write-Host "Connecting to Chrome DevTools..." -ForegroundColor Yellow
    $Tabs = Invoke-RestMethod "http://localhost:$Port/json"
    $WdTab = $Tabs | Where-Object { $_.url -match "whydonate" } | Select-Object -First 1
    
    if (-not $WdTab) {
        Write-Error "No Whydonate tab found. Please open https://whydonate.com/en/dashboard first."
        exit 1
    }
    
    Write-Host "Found Whydonate tab: $($WdTab.title)" -ForegroundColor Green
    
    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $ws.ConnectAsync([Uri]$WdTab.webSocketDebuggerUrl, [System.Threading.CancellationToken]::None).Wait()
    Write-Host "WebSocket connected" -ForegroundColor Green

    # JavaScript to extract campaign data from Whydonate dashboard
    $extractJs = @"
        (function() {
            const campaigns = [];
            
            // Look for campaign cards/rows in the dashboard
            const cards = document.querySelectorAll('[class*="campaign"], [class*="fundraiser"], tr[data-id], .card, .project-item');
            
            cards.forEach((card, idx) => {
                try {
                    // Try various selectors for title
                    const titleEl = card.querySelector('h1, h2, h3, h4, h5, .title, [class*="title"], a[href*="fundraising"]');
                    const title = titleEl ? titleEl.innerText.trim() : null;
                    
                    // Try to get URL
                    const linkEl = card.querySelector('a[href*="fundraising"], a[href*="campaign"]');
                    const url = linkEl ? linkEl.href : null;
                    
                    // Try to get amounts
                    const amountEl = card.querySelector('[class*="amount"], [class*="raised"], .progress-amount');
                    const raised = amountEl ? amountEl.innerText.trim() : null;
                    
                    // Try to get ID from data attributes or URL
                    let id = card.dataset?.id || card.dataset?.campaignId;
                    if (!id && url) {
                        const match = url.match(/fundraising-for\/([^\/\?]+)/);
                        id = match ? match[1] : null;
                    }
                    
                    if (title || url) {
                        campaigns.push({
                            title: title,
                            url: url,
                            raised_text: raised,
                            id: id,
                            index: idx
                        });
                    }
                } catch(e) {}
            });
            
            // Also try to find data in tables
            const rows = document.querySelectorAll('table tbody tr');
            rows.forEach((row, idx) => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    const linkEl = row.querySelector('a[href*="fundraising"]');
                    campaigns.push({
                        title: cells[0]?.innerText?.trim(),
                        url: linkEl?.href,
                        raised_text: cells[1]?.innerText?.trim(),
                        id: row.dataset?.id,
                        index: 'table_' + idx
                    });
                }
            });
            
            return { 
                campaigns: campaigns, 
                pageUrl: window.location.href,
                pageTitle: document.title 
            };
        })()
"@

    Write-Host "Extracting campaign data..." -ForegroundColor Yellow
    $result = Invoke-CDPCmd $ws "Runtime.evaluate" @{expression = $extractJs; returnByValue = $true}
    
    if ($result.result.result.value) {
        $data = $result.result.result.value
        Write-Host "Page: $($data.pageTitle)" -ForegroundColor Cyan
        Write-Host "URL: $($data.pageUrl)" -ForegroundColor Cyan
        Write-Host "Found $($data.campaigns.Count) campaigns" -ForegroundColor Green
        
        # Save to file
        $data | ConvertTo-Json -Depth 10 | Out-File $OutputFile -Encoding utf8
        Write-Host "Saved to $OutputFile" -ForegroundColor Green
        
        # Display summary
        $data.campaigns | ForEach-Object { Write-Host "  - $($_.title)" -ForegroundColor Gray }
    }
    else {
        Write-Warning "No data extracted. The dashboard may not be fully loaded or the page structure differs."
        Write-Host "Response: $($result | ConvertTo-Json -Depth 5)" -ForegroundColor Gray
    }
}
catch {
    Write-Error "Error: $_"
}
finally {
    if ($ws) { $ws.Dispose() }
}
