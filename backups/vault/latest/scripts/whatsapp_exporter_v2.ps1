<#
.SYNOPSIS
    WhatsApp Business Chat Exporter v2
.DESCRIPTION
    Improved exporter with multiple selector strategies for WhatsApp Business Web
#>

param (
    [string]$Port = "9222",
    [string]$ExportDir = "data\exports",
    [int]$MaxChats = 0,  # 0 = all
    [switch]$DebugMode
)

function Invoke-CDPCmd {
    param($ws, $method, $params, $cts)
    try {
        $id = Get-Random
        $msg = @{ id = $id; method = $method; params = $params } | ConvertTo-Json -Compress -Depth 10
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
        $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
        $buf = [byte[]]::new(1MB)
        $segment = [ArraySegment[byte]]::new($buf)
        $res = $ws.ReceiveAsync($segment, $cts.Token)
        $res.Wait()
        $response = [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
        return $response
    }
    catch { 
        Write-Warning "CDP Error: $_"
        return $null 
    }
}

if (-not (Test-Path $ExportDir)) { 
    New-Item -Path $ExportDir -ItemType Directory -Force | Out-Null 
}

try {
    Write-Host "`n=== WhatsApp Business Exporter v2 ===" -ForegroundColor Cyan
    Write-Host "Connecting to Chrome DevTools on port $Port..." -ForegroundColor Yellow
    
    $Tabs = Invoke-RestMethod "http://localhost:$Port/json"
    $WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" -and $_.type -eq "page" } | Select-Object -First 1
    
    if (-not $WaTab) {
        Write-Error "No WhatsApp tab found. Please open web.whatsapp.com first."
        exit 1
    }
    
    Write-Host "Found: $($WaTab.title)" -ForegroundColor Green
    Write-Host "URL: $($WaTab.url)" -ForegroundColor Gray
    
    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, [System.Threading.CancellationToken]::None).Wait()
    Write-Host "WebSocket connected" -ForegroundColor Green

    # Enhanced chat discovery with multiple strategies
    $discoverJs = @'
(function() {
    const strategies = [];
    
    // Strategy 1: aria-label based (WhatsApp Business uses accessibility labels)
    const chatPanes = document.querySelectorAll('[aria-label*="Chat list"], [aria-label*="chat list"]');
    chatPanes.forEach(pane => {
        const items = pane.querySelectorAll('[role="listitem"], [role="row"], [data-testid*="list-item"]');
        items.forEach(item => {
            const titleEl = item.querySelector('[title], [data-testid*="cell-frame-title"]');
            if (titleEl && titleEl.title) {
                strategies.push({ name: titleEl.title, strategy: "aria-label" });
            }
        });
    });
    
    // Strategy 2: data-testid based
    document.querySelectorAll('[data-testid="cell-frame-container"]').forEach(cell => {
        const title = cell.querySelector('[title]');
        if (title && title.title) {
            strategies.push({ name: title.title, strategy: "data-testid" });
        }
    });
    
    // Strategy 3: Span with title attribute in chat list
    document.querySelectorAll('div[tabindex="-1"] span[title]').forEach(span => {
        if (span.title && span.title.length > 0 && span.title.length < 100) {
            strategies.push({ name: span.title, strategy: "span-title" });
        }
    });
    
    // Strategy 4: Direct row detection
    document.querySelectorAll('[role="row"]').forEach(row => {
        const text = row.innerText.split('\n')[0];
        if (text && text.length > 1 && text.length < 80) {
            const excluded = ['Archived', 'Unread', 'Groups', 'Search', 'Settings', 'New chat', 'Status'];
            if (!excluded.some(ex => text.includes(ex))) {
                strategies.push({ name: text, strategy: "role-row" });
            }
        }
    });
    
    // Deduplicate by name
    const seen = new Set();
    const unique = [];
    strategies.forEach(s => {
        const clean = s.name.trim();
        if (clean && !seen.has(clean)) {
            seen.add(clean);
            unique.push({ name: clean, strategy: s.strategy });
        }
    });
    
    return {
        total: unique.length,
        chats: unique.slice(0, 50),  // Return first 50 for initial check
        debug: {
            chatPanes: chatPanes.length,
            testIdCells: document.querySelectorAll('[data-testid="cell-frame-container"]').length,
            roleRows: document.querySelectorAll('[role="row"]').length
        }
    };
})()
'@

    Write-Host "`nDiscovering chats..." -ForegroundColor Yellow
    $discovery = Invoke-CDPCmd $ws "Runtime.evaluate" @{expression = $discoverJs; returnByValue = $true }
    $result = $discovery.result.result.value
    
    if ($DebugMode) {
        Write-Host "`nDebug info:" -ForegroundColor Magenta
        Write-Host "  Chat panes: $($result.debug.chatPanes)" -ForegroundColor Gray
        Write-Host "  TestID cells: $($result.debug.testIdCells)" -ForegroundColor Gray
        Write-Host "  Role rows: $($result.debug.roleRows)" -ForegroundColor Gray
    }
    
    Write-Host "`nFound $($result.total) unique chats" -ForegroundColor Green
    
    if ($result.chats.Count -eq 0) {
        Write-Warning "No chats found. WhatsApp may not be fully loaded or logged in."
        Write-Host "Please ensure:"
        Write-Host "  1. You are logged into WhatsApp Web"
        Write-Host "  2. The chat list is visible (not in a specific chat)"
        Write-Host "  3. Wait a few seconds for the page to fully load"
        exit 1
    }
    
    # Show first few chats
    Write-Host "`nFirst 10 chats:" -ForegroundColor Cyan
    $result.chats | Select-Object -First 10 | ForEach-Object { 
        Write-Host "  - $($_.name) [via $($_.strategy)]" -ForegroundColor Gray 
    }
    
    # Export each chat
    $limit = if ($MaxChats -gt 0) { [Math]::Min($MaxChats, $result.total) } else { $result.total }
    $exported = 0
    $skipped = 0
    
    Write-Host "`nStarting export of $limit chats..." -ForegroundColor Yellow
    
    for ($i = 0; $i -lt $limit; $i++) {
        $chat = $result.chats[$i]
        if (-not $chat) { continue }
        
        $name = $chat.name
        $safeName = $name -replace '[^\w\s-]', '' -replace '\s+', '_'
        if (-not $safeName -or $safeName.Length -lt 2) { $safeName = "Chat_$i" }
        $path = Join-Path $ExportDir "$safeName.csv"
        
        if (Test-Path $path) {
            $skipped++
            continue
        }
        
        Write-Host "`n[$($i+1)/$limit] Opening: $name" -ForegroundColor Cyan
        
        # Click on chat
        $clickJs = @"
(function(target) {
    const cells = document.querySelectorAll('[data-testid="cell-frame-container"], [role="listitem"], [role="row"]');
    for (const cell of cells) {
        const titleEl = cell.querySelector('[title]');
        if (titleEl && titleEl.title === target) {
            cell.click();
            return "clicked";
        }
        if (cell.innerText.includes(target)) {
            cell.click();
            return "clicked_text";
        }
    }
    // Try span with title
    const spans = document.querySelectorAll('span[title="' + target + '"]');
    if (spans.length > 0) {
        spans[0].closest('[tabindex]')?.click();
        return "clicked_span";
    }
    return "not_found";
})(arguments[0])
"@
        $clickJs = $clickJs -replace 'arguments\[0\]', "`"$($name -replace '"', '\"')`""
        
        $clickResult = Invoke-CDPCmd $ws "Runtime.evaluate" @{expression = $clickJs; returnByValue = $true }
        Write-Host "  Click result: $($clickResult.result.result.value)" -ForegroundColor Gray
        
        Start-Sleep -Seconds 3
        
        # Extract messages
        $extractJs = @'
(function() {
    const messages = [];
    const seen = new Set();
    
    // Find message containers
    const msgContainers = document.querySelectorAll('[data-testid="msg-container"], .message-in, .message-out, [class*="message"]');
    
    msgContainers.forEach(msg => {
        const text = msg.querySelector('.selectable-text, [data-testid="msg-text"]')?.innerText?.trim();
        const meta = msg.querySelector('[data-pre-plain-text]')?.getAttribute('data-pre-plain-text');
        const time = msg.querySelector('[data-testid="msg-meta"], .msg-time')?.innerText?.trim();
        
        if (text && !seen.has(text)) {
            seen.add(text);
            let sender = "Unknown";
            let timestamp = time || "";
            
            if (meta) {
                const match = meta.match(/\[(.*?)\]\s*(.*?):/);
                if (match) {
                    timestamp = match[1];
                    sender = match[2];
                }
            }
            
            messages.push({ timestamp, sender, text });
        }
    });
    
    // Also try copyable-text approach
    document.querySelectorAll('.copyable-text').forEach(el => {
        const text = el.innerText?.trim();
        const meta = el.getAttribute('data-pre-plain-text') || '';
        
        if (text && !seen.has(text)) {
            seen.add(text);
            let sender = "Unknown";
            let timestamp = "";
            
            const match = meta.match(/\[(.*?)\]\s*(.*?):/);
            if (match) {
                timestamp = match[1];
                sender = match[2];
            }
            
            messages.push({ timestamp, sender, text });
        }
    });
    
    return messages;
})()
'@
        
        $msgResult = Invoke-CDPCmd $ws "Runtime.evaluate" @{expression = $extractJs; returnByValue = $true }
        $msgs = $msgResult.result.result.value
        
        if ($msgs -and $msgs.Count -gt 0) {
            $lines = @("Timestamp,Sender,Message")
            foreach ($m in $msgs) {
                $ts = ($m.timestamp -replace '"', '""')
                $sn = ($m.sender -replace '"', '""')
                $tx = ($m.text -replace '[\r\n]+', ' ' -replace '"', '""')
                $lines += "`"$ts`",`"$sn`",`"$tx`""
            }
            $lines | Out-File $path -Encoding utf8
            Write-Host "  SUCCESS: Saved $($msgs.Count) messages to $safeName.csv" -ForegroundColor Green
            $exported++
        }
        else {
            Write-Host "  No messages extracted" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`n=== Export Complete ===" -ForegroundColor Cyan
    Write-Host "Exported: $exported chats" -ForegroundColor Green
    Write-Host "Skipped (existing): $skipped chats" -ForegroundColor Yellow
}
catch {
    Write-Error "Error: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
}
finally {
    if ($ws) { $ws.Dispose() }
}
