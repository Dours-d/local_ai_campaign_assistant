
param([string]$Port = "9222")

# Connect (same as before)
$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" -and $_.type -eq "page" } | Select-Object -First 1
if (-not $WaTab) { Write-Error "No WhatsApp tab"; exit 1 }
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
$cts.CancelAfter(30000)
$ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, $cts.Token).Wait()

function Send-CDP {
    param($expr)
    $msg = @{ id = Get-Random; method = "Runtime.evaluate"; params = @{ expression = $expr; returnByValue = $true } } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    $buf = [byte[]]::new(2MB) # increased buffer
    $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $res.Wait()
    return [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
}

Write-Host "Hunting for Chat Window (Deep Scan)..." -ForegroundColor Cyan

$js = @'
(function() {
    const findings = [];
    
    // Strategy 1: Look for "application" role which is often the main message list
    const apps = document.querySelectorAll('div[role="application"]');
    apps.forEach(div => findings.push({ type: "Role=Application", div: div }));
    
    // Strategy 2: Look for elements on the RIGHT side of the screen (Left > 400)
    // and have substantial height
    const allDivs = document.querySelectorAll('div');
    const rightSide = Array.from(allDivs).filter(d => {
        const r = d.getBoundingClientRect();
        return r.left > 400 && r.height > 400 && r.width > 300;
    });
    // Pick unique largest ones
    rightSide.sort((a,b) => (b.clientWidth*b.clientHeight) - (a.clientWidth*a.clientHeight));
    if (rightSide.length > 0) {
        // limit to top 5
        rightSide.slice(0, 5).forEach(d => findings.push({ type: "RightSideCandidate", div: d }));
    }
    
    // Extract details
    return findings.map(f => {
        const d = f.div;
        const r = d.getBoundingClientRect();
        let text = d.innerText ? d.innerText.substring(0, 60).replace(/\n/g, ' ') : "NO_TEXT";
        
        return {
            type: f.type,
            classes: d.className,
            rect: `L:${Math.round(r.left)} T:${Math.round(r.top)} W:${Math.round(r.width)} H:${Math.round(r.height)}`,
            scroll: `H:${d.scrollHeight} T:${d.scrollTop}`,
            attr: `Role:${d.getAttribute('role')} TabIdx:${d.getAttribute('tabindex')}`,
            sample: text
        };
    });
})()
'@

$res = Send-CDP $js
$items = $res.result.result.value

Write-Host "Found Candidates:" -ForegroundColor Yellow
$items | Format-Table -AutoSize
