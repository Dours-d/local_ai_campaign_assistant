
# Diagnostic: Inspect Children of '_ajx_'
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

Write-Host "Diagnostic: Deep Inspect Children for '$ChatName'" -ForegroundColor Cyan

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

# Inspect Children
$inspectJs = @'
(function() {
    function findChatContainer() {
        const apps = document.querySelectorAll('div[role="application"]');
        for (const app of apps) {
            if (app.innerText.includes("message-in") || app.innerText.includes("message-out")) return app;
        }
        return document.querySelector('div._ajx_');
    }

    const container = findChatContainer();
    if (!container) return { error: "Container not found" };
    
    const children = [];
    for (let i = 0; i < container.children.length; i++) {
        const child = container.children[i];
        children.push({
            index: i,
            tagName: child.tagName,
            className: child.className,
            scrollHeight: child.scrollHeight,
            childCount: child.children.length,
            textSample: child.innerText.substring(0, 100),
            hasMessageIn: child.innerHTML.includes("message-in")
        });
    }

    return { 
        containerClass: container.className,
        totalChildren: container.children.length,
        children: children
    };
})()
'@

$res = Send-CDP $inspectJs
$res.result.result.value | ConvertTo-Json -Depth 5
