
# Diagnostic: Inspect '_ajx_ x1q80dvb' Container
param(
    [string]$Port = "9222",
    [string]$ChatName = "Lawyer Nizar" 
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

Write-Host "Diagnostic: Inspecting Container for '$ChatName'" -ForegroundColor Cyan

# Click Chat
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
Send-CDP $clickJs | Out-Null
Start-Sleep -Seconds 2

# Inspect Container Structure
$inspectJs = @'
(function() {
    // 1. Find the known container class from logs
    // The class reported was "_ajx_ x1q80dvb" (partial match likely)
    // We look for role=application with message-in inside
    
    function findChatContainer() {
        const apps = document.querySelectorAll('div[role="application"]');
        for (const app of apps) {
            if (app.innerText.includes("message-in") || app.innerText.includes("message-out") || app.innerText.includes("end-to-end encrypted")) {
                return app;
            }
        }
        return document.querySelector('div._ajx_'); // Try the class directly
    }

    const container = findChatContainer();
    if (!container) return { error: "Container not found" };

    const nodes = container.querySelectorAll('div[data-pre-plain-text]');
    
    // Dump first 3 nodes structure
    const samples = [];
    nodes.forEach((n, i) => {
        if (i < 3) {
            samples.push({
                tag: n.tagName,
                className: n.className,
                attr: n.getAttribute('data-pre-plain-text'),
                textLen: n.innerText.length,
                htmlSample: n.outerHTML.substring(0, 200)
            });
        }
    });

    return { 
        containerClass: container.className,
        totalNodes: nodes.length,
        childCount: container.children.length,
        firstChildHTML: container.children[0] ? container.children[0].outerHTML.substring(0, 500) : "No children",
        samples: samples
    };
})()
'@

$res = Send-CDP $inspectJs
$res.result.result.value | ConvertTo-Json -Depth 5
