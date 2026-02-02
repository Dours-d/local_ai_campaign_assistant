# Load all Whydonate campaigns by clicking "View more" repeatedly
param([int]$Clicks = 18)

$Port = "9222"

try {
    $Tabs = Invoke-RestMethod "http://localhost:$Port/json" -ErrorAction Stop
    $WdTab = $Tabs | Where-Object { $_.url -match "whydonate" } | Select-Object -First 1
    
    if (-not $WdTab) {
        Write-Host "ERROR: No Whydonate tab found!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Connected: $($WdTab.title)" -ForegroundColor Green
    
    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $cts = New-Object System.Threading.CancellationTokenSource
    $ws.ConnectAsync([Uri]$WdTab.webSocketDebuggerUrl, $cts.Token).Wait()
    
    function Send-CDP($js) {
        $msg = @{ id = Get-Random; method = "Runtime.evaluate"; params = @{ expression = $js; returnByValue = $true; awaitPromise = $true } } | ConvertTo-Json -Compress -Depth 10
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
        $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
        $allBytes = New-Object System.Collections.Generic.List[byte]
        $buffer = [byte[]]::new(1MB)
        do {
            $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cts.Token).Result
            if ($res.Count -gt 0) { $allBytes.AddRange($buffer[0..($res.Count - 1)]) }
        } while (-not $res.EndOfMessage)
        return [System.Text.Encoding]::UTF8.GetString($allBytes.ToArray()) | ConvertFrom-Json
    }
    
    Write-Host "Clicking 'View more' up to $Clicks times..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le $Clicks; $i++) {
        $clickJs = "(function(){ var b = Array.from(document.querySelectorAll('button,a,span,div')).find(x => x.innerText && x.innerText.trim().toLowerCase() === 'view more'); if(b){b.click();return 'clicked';} return 'not found'; })()"
        $r = Send-CDP $clickJs
        $status = $r.result.result.value
        
        if ($status -eq "clicked") {
            Write-Host "  [$i] Clicked" -ForegroundColor Cyan
            Start-Sleep -Milliseconds 1500
        }
        else {
            Write-Host "  [$i] No button found - all loaded!" -ForegroundColor Green
            break
        }
    }
    
    Start-Sleep -Seconds 2
    Write-Host "`nExtracting all campaigns..." -ForegroundColor Yellow
    
    $extractJs = @"
(function() {
    var campaigns = [];
    var seen = {};
    
    // Get all links that look like campaigns
    document.querySelectorAll('a').forEach(function(a) {
        var href = a.href || '';
        var text = a.innerText ? a.innerText.trim() : '';
        
        // Match fundraising URLs
        if (href.includes('fundraising-for/') && text && text.length > 5 && !seen[href]) {
            seen[href] = 1;
            campaigns.push({
                title: text,
                url: href,
                slug: href.split('fundraising-for/')[1]?.split('/')[0] || ''
            });
        }
    });
    
    return campaigns;
})()
"@
    
    $data = Send-CDP $extractJs
    $campaigns = $data.result.result.value
    
    Write-Host "Found $($campaigns.Count) campaigns!" -ForegroundColor Green
    
    # Save to file
    $outPath = Join-Path $PSScriptRoot "..\data\whydonate_all_campaigns.json"
    $campaigns | ConvertTo-Json -Depth 5 | Out-File $outPath -Encoding UTF8
    Write-Host "Saved to $outPath" -ForegroundColor Green
    
    # Show first few
    Write-Host "`nFirst 5 campaigns:" -ForegroundColor Cyan
    $campaigns | Select-Object -First 5 | ForEach-Object { Write-Host "  - $($_.title)" }
    
    $ws.Dispose()
}
catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
}
