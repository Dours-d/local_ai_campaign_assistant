
# Diagnostic: Dump HTML of the Message Container
param(
    [string]$Port = "9222",
    [string]$ChatName = "Adil L." # Default to one that failed
)

$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" -and $_.type -eq "page" } | Select-Object -First 1
if (-not $WaTab) { Write-Error "No WhatsApp tab"; exit }
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
$ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, $cts.Token).Wait()

function Send-CDP {
    param($expr)
    $msg = @{ id = Get-Random; method = "Runtime.evaluate"; params = @{ expression = $expr; returnByValue = $true } } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    $buf = [byte[]]::new(5MB)
    $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $res.Wait()
    return [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
}

Write-Host "Diagnostic: Dumping HTML for '$ChatName'" -ForegroundColor Cyan

# 1. Click Chat
$clickJs = @"
(function() {
    const spans = document.querySelectorAll('span[title]');
    for (const span of spans) {
        if (span.title === `"$($ChatName -replace '"', '\"')`") {
            span.click();
            return 'clicked';
        }
    }
    return 'not_found';
})()
"@
$res = Send-CDP $clickJs
if ($res.result.result.value -ne 'clicked') { Write-Warning "Chat not found/clicked"; exit }
Start-Sleep -Seconds 2

# 2. Dump HTML
$dumpJs = @'
(function() {
    // Find verified container
    const allDivs = Array.from(document.querySelectorAll('div'));
    const candidates = allDivs.filter(div => {
        const r = div.getBoundingClientRect();
        return r.left > 300 && r.height > 200 && div.scrollHeight > div.clientHeight;
    });
    candidates.sort((a,b) => b.scrollHeight - a.scrollHeight);
    
    // Fallback search
    if (!candidates[0]) {
         const areaCandidates = allDivs.filter(div => {
            const r = div.getBoundingClientRect();
            return r.left > 300 && r.width > 300 && r.height > 400;
        });
        areaCandidates.sort((a,b) => (b.clientWidth * b.clientHeight) - (a.clientWidth * a.clientHeight));
        if (areaCandidates[0]) candidates.push(areaCandidates[0]);
    }

    if (candidates[0]) {
        // Return first 5000 chars of HTML to inspect structure
        return { 
            html: candidates[0].innerHTML.substring(0, 5000), 
            len: candidates[0].innerHTML.length, 
            childCount: candidates[0].children.length,
            sampleText: candidates[0].innerText.substring(0, 500)
        };
    }
    return { error: "No container" };
})()
'@

$res = Send-CDP $dumpJs
$val = $res.result.result.value
$path = "debug_html_dump.txt"
$val | Out-File $path
Write-Host "Dump saved to $path"
Write-Host "HTML Sample:" -ForegroundColor Gray
$val.html.Substring(0, [math]::Min($val.html.Length, 1000))
