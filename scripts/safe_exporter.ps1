
# WhatsApp Safe Exporter (JSON)
# Version: 6.0 (The "Definitive" Robust Version)

param(
    [string]$Port = "9222",
    [string]$ExportDir = "data/exports"
)

if (-not (Test-Path $ExportDir)) { New-Item -ItemType Directory -Path $ExportDir }

# 1. Connect to CDP
$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" -and $_.type -eq "page" } | Select-Object -First 1
if (-not $WaTab) { Write-Error "No WhatsApp tab found on port $Port. Open WhatsApp Web first."; exit }

$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
$ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, $cts.Token).Wait()

function Send-CDP {
    param([string]$expr)
    $msg = @{ id = Get-Random; method = "Runtime.evaluate"; params = @{ expression = $expr; returnByValue = $true } } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    $buf = [byte[]]::new(5MB)
    $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $res.Wait()
    return [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
}

# 2. Discover Chats
Write-Host "=== WhatsApp Safe Exporter (JSON) ===" -ForegroundColor Cyan
Write-Host "Discovering chats..."
$getChatsJs = @'
(function() {
    const list = document.querySelectorAll('span[title]');
    return Array.from(list).map(s => s.title).filter(t => t && t.length > 0 && !t.includes(":") && t !== "WhatsApp");
})()
'@
$cRes = Send-CDP $getChatsJs
$chats = $cRes.result.result.value | Select-Object -Unique
Write-Host "Found $($chats.Count) chats."

# 3. Common Support JS
$commonJs = @'
function findChatContainer() {
    // Tournament Selection: Broadened and Deepest-Preferred
    const allDivs = Array.from(document.querySelectorAll('div'));
    const candidates = [];
    for (const div of allDivs) {
        const r = div.getBoundingClientRect();
        // Filters: must be on right half and minimum size
        if (r.width > 100 && r.height > 100 && r.left > 100) {
            const bubbles = div.querySelectorAll('[data-testid*="msg"], .message-in, .message-out, .copyable-text, [data-pre-plain-text]');
            if (bubbles.length > 0) {
                candidates.push({ div: div, count: bubbles.length, textLen: div.innerText.length });
            }
        }
    }
    // Sort by count DESC, then textLen ASC (smaller/deeper is better if tied)
    candidates.sort((a,b) => (b.count - a.count) || (a.textLen - b.textLen));
    return candidates.length > 0 ? candidates[0].div : null;
}
function getScrollableContainer(target) {
    if (!target) return null;
    if (target.scrollHeight > target.clientHeight + 10) return target;
    const child = Array.from(target.querySelectorAll('div')).find(d => d.scrollHeight > d.clientHeight + 10);
    if (child) return child;
    let p = target.parentElement;
    while(p && p.tagName !== 'BODY') {
        if (p.scrollHeight > p.clientHeight + 10) return p;
        p = p.parentElement;
    }
    return target;
}
'@

foreach ($chatName in $chats) {
    $safeName = $chatName -replace '[^a-zA-Z0-9_\-]', '_'
    Write-Host "`nOpening: $chatName" -ForegroundColor Yellow
    
    # Click Chat
    $jsonName = $chatName | ConvertTo-Json -Compress
    $clickJs = "(function() { const target = $jsonName; const s = Array.from(document.querySelectorAll('span[title]')).find(x => x.title === target); if(s){s.click(); return 'ok'} return 'err' })()"
    $clickRes = Send-CDP $clickJs
    if ($clickRes.result.result.value -ne "ok") { Write-Warning "Could not click $chatName"; continue }
    
    # CRITICAL DELAY: Give virtualization time to render messages
    Start-Sleep -Seconds 2.5

    # Auto-Scroll Up
    Write-Host "Auto-Loading History (scrolling up)..." -NoNewline
    $scrollJs = $commonJs + @'
(function() {
    let container = getScrollableContainer(findChatContainer());
    if (!container) return { status: "no_container" };
    if (container.scrollTop > 50) {
        container.scrollTop = 0;
        return { status: "scrolling", h: container.scrollHeight };
    }
    return { status: "at_top", h: container.scrollHeight };
})()
'@
    $lastH = 0; $stables = 0
    for ($i = 0; $i -lt 30; $i++) {
        $sRes = Send-CDP $scrollJs; $val = $sRes.result.result.value
        if ($val.status -eq "no_container") { break }
        if ($val.status -eq "at_top" -and $val.h -eq $lastH) { $stables++; if ($stables -gt 2) { break } } else { $stables = 0 }
        $lastH = $val.h; Write-Host "." -NoNewline -ForegroundColor Gray; Start-Sleep -Milliseconds 800
    }
    Write-Host " Loaded." -ForegroundColor Green

    # Extract
    Write-Host "Extracting..." -NoNewline
    $extractJs = $commonJs + @'
(function() {
    const list = findChatContainer();
    if (!list) return { type: "error", msg: "No list found" };
    
    const messages = [];
    const rows = list.querySelectorAll('div[role="row"]');
    rows.forEach(row => {
        const bubble = row.querySelector('div.message-in, div.message-out, [data-testid*="msg"]');
        if (!bubble) return;
        const metaNode = row.querySelector('div[data-pre-plain-text]');
        let timestamp = "", sender = (bubble.classList && bubble.classList.contains('message-out')) ? "Me" : "Them", text = row.innerText.trim();
        if (metaNode) {
            const m = metaNode.getAttribute('data-pre-plain-text').match(/^\[(.*?)\] (.*?):/);
            if (m) { timestamp = m[1]; sender = m[2]; }
        }
        if (timestamp && text.endsWith(timestamp)) text = text.substring(0, text.length - timestamp.length).trim();
        if (text) messages.push({ timestamp, sender, text });
    });

    if (messages.length < 5 && list.innerText.length > 300) {
        // Regex Fallback
        const lines = list.innerText.split('\n');
        let cur = { text: "", sender: "Unknown", timestamp: "" }, regexMsgs = [];
        lines.forEach(l => {
            const tm = l.match(/^(\d{1,2}:\d{2}(?:\s?[aApP][mM])?)$/);
            if (tm) { cur.timestamp = tm[1]; if(cur.text){regexMsgs.push({...cur}); cur={text:"",sender:"Unknown",timestamp:""}} }
            else if (!l.match(/^(Today|Yesterday|\d{1,2}\/\d{1,2}\/\d{4})$/) && l.trim()) { cur.text += (cur.text?"\n":"") + l.trim(); }
        });
        if (cur.text) regexMsgs.push(cur);
        if (regexMsgs.length > messages.length) return { type: "json", strat: "regex", data: regexMsgs, count: regexMsgs.length };
    }
    return messages.length > 0 ? { type: "json", strat: "dom", data: messages, count: messages.length } : { type: "text", data: list.innerText, count: list.innerText.length };
})()
'@
    $eRes = Send-CDP $extractJs; $val = $eRes.result.result.value
    if ($val.type -eq "json") {
        $path = Join-Path $ExportDir "$safeName.json"
        $val.data | ConvertTo-Json -Depth 5 -AsArray | Set-Content -Path $path -Encoding utf8
        Write-Host " SUCCESS ($($val.count) messages via $($val.strat))" -ForegroundColor Green
    }
    else {
        $path = Join-Path $ExportDir "$safeName.txt"
        $val.data | Set-Content -Path $path -Encoding utf8
        Write-Host " TXT Fallback ($($val.count) chars)" -ForegroundColor Yellow
    }
}
Write-Host "`nAll Done." -ForegroundColor Cyan
