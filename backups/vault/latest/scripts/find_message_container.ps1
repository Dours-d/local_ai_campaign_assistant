
param([string]$Port = "9222")

# Connect
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
    $buf = [byte[]]::new(2MB)
    $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $res.Wait()
    return [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
}

Write-Host "Searching for Message Container via Content..." -ForegroundColor Cyan

$js = @'
(function() {
    // 1. Find the "end-to-end encrypted" system message
    // It's usually "Messages are end-to-end encrypted. No one outside of this chat..."
    // We search for a span/div containing "end-to-end encrypted"
    
    function findText(node, text) {
        if (node.nodeType === 3) { // Text node
            if (node.textContent.includes(text)) return node.parentElement;
        }
        for (let child of node.childNodes) {
            const found = findText(child, text);
            if (found) return found;
        }
        return null;
    }
    
    // Search in body
    const anchor = findText(document.body, "end-to-end encrypted");
    if (!anchor) return "Anchor text not found. Is a chat open?";
    
    let path = [];
    let curr = anchor;
    let foundContainer = null;
    
    // Walk up 15 levels to find the scrollable container
    for (let i=0; i<15; i++) {
        if (!curr) break;
        
        const style = window.getComputedStyle(curr);
        const isScrollable = (curr.scrollHeight > curr.clientHeight) && 
                           (style.overflowY === 'auto' || style.overflowY === 'scroll' || style.overflow === 'auto');
                           
        // WhatsApp might use specific class marker like "copyable-area" or role="application"
        const role = curr.getAttribute('role');
        const labels = Array.from(curr.classList).join('.');
        
        let info = `${curr.tagName}.${labels} (H:${curr.scrollHeight}/${curr.clientHeight}) role=${role}`;
        path.push(info);
        
        if (role === 'application' || (curr.scrollHeight > curr.clientHeight + 50 && curr.clientWidth > 400)) {
            // Likely the one
            foundContainer = curr;
            // Don't break immediately, log it
        }
        
        curr = curr.parentElement;
    }
    
    return {
        anchor: anchor.tagName,
        path: path,
        suggestion: foundContainer ? foundContainer.className : "None"
    };
})()
'@

$res = Send-CDP $js
$val = $res.result.result.value

if ($val.path) {
    Write-Host "Traversal Path (Bottom -> Up):" -ForegroundColor Yellow
    $val.path | ForEach-Object { Write-Host "  ^ $_" -ForegroundColor Gray }
    Write-Host "`nSuggested Container Class: $($val.suggestion)" -ForegroundColor Green
}
else {
    Write-Host "Result: $val" -ForegroundColor Red
}
