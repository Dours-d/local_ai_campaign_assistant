<#
.SYNOPSIS
    WhatsApp Business Chat Exporter v3 - Working Version
.DESCRIPTION
    Exports chats from WhatsApp Business Web using Chrome DevTools Protocol.
    Based on tested CDP communication patterns.
#>

param (
    [string]$Port = "9222",
    [string]$ExportDir = "data\exports",
    [int]$MaxChats = 0,  # 0 = all visible
    [int]$ChatWaitSec = 3,
    [switch]$ListOnly
)

if (-not (Test-Path $ExportDir)) { 
    New-Item -Path $ExportDir -ItemType Directory -Force | Out-Null 
}

$cts = New-Object System.Threading.CancellationTokenSource
$cts.CancelAfter(1800000)  # 30 minute global timeout

function Send-CDPCommand {
    param($ws, $expression)
    
    $msg = @{ 
        id     = Get-Random
        method = "Runtime.evaluate"
        params = @{ expression = $expression; returnByValue = $true }
    } | ConvertTo-Json -Compress -Depth 10
    
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    
    $buf = [byte[]]::new(2MB)
    $result = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $result.Wait()
    
    $response = [System.Text.Encoding]::UTF8.GetString($buf, 0, $result.Result.Count) | ConvertFrom-Json
    return $response.result.result.value
}

try {
    Write-Host "`n=== WhatsApp Business Exporter v3 ===" -ForegroundColor Cyan
    
    $Tabs = Invoke-RestMethod "http://localhost:$Port/json"
    $WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" -and $_.type -eq "page" } | Select-Object -First 1
    
    if (-not $WaTab) {
        Write-Error "No WhatsApp page found. Open web.whatsapp.com first."
        exit 1
    }
    
    Write-Host "Found: $($WaTab.title)" -ForegroundColor Green
    
    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, $cts.Token).Wait()
    Write-Host "WebSocket connected" -ForegroundColor Green

    # Get all chat names using span[title] which we know works
    Write-Host "`nDiscovering chats..." -ForegroundColor Yellow
    
    $discoverJs = @'
(function() {
    const chats = [];
    const seen = new Set();
    
    // Get all span elements with title (chat names)
    document.querySelectorAll('span[title]').forEach(span => {
        const title = span.title.trim();
        // Filter out non-chat titles
        if (title && 
            title.length > 1 && 
            title.length < 80 &&
            !seen.has(title) &&
            !['Search', 'Settings', 'New chat', 'Status', 'Menu', 'Archived'].includes(title) &&
            !title.startsWith('http') &&
            !title.match(/^\d{1,2}\/\d{1,2}\/\d{2,4}/) &&
            !title.match(/^\d{1,2}:\d{2}/)) {
            seen.add(title);
            chats.push(title);
        }
    });
    return chats;
})()
'@
    
    $chatList = Send-CDPCommand $ws $discoverJs
    
    if (-not $chatList -or $chatList.Count -eq 0) {
        Write-Warning "No chats found. Make sure WhatsApp is logged in and chat list is visible."
        exit 1
    }
    
    Write-Host "Found $($chatList.Count) chats" -ForegroundColor Green
    
    if ($ListOnly) {
        Write-Host "`nChat list:" -ForegroundColor Cyan
        $chatList | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
        exit 0
    }
    
    # Determine how many to export
    $total = if ($MaxChats -gt 0 -and $MaxChats -lt $chatList.Count) { $MaxChats } else { $chatList.Count }
    
    Write-Host "`nExporting $total chats..." -ForegroundColor Yellow
    
    $exported = 0
    $skipped = 0
    $failed = 0
    
    for ($i = 0; $i -lt $total; $i++) {
        $chatName = $chatList[$i]
        $safeName = $chatName -replace '[^\w\s-]', '' -replace '\s+', '_'
        if (-not $safeName -or $safeName.Length -lt 2) { $safeName = "Chat_$i" }
        $csvPath = Join-Path $ExportDir "$safeName.csv"
        
        if (Test-Path $csvPath) {
            Write-Host "[$($i+1)/$total] SKIP (exists): $chatName" -ForegroundColor DarkGray
            $skipped++
            continue
        }
        
        Write-Host "[$($i+1)/$total] Exporting: $chatName" -ForegroundColor Cyan
        
        # Click on chat
        $clickJs = @"
(function() {
    const spans = document.querySelectorAll('span[title]');
    for (const span of spans) {
        if (span.title === `"$($chatName -replace '"', '\"')`") {
            // Try clicking the span itself first (often works)
            span.click();
            
            // Also click the row wrapper just in case
            const row = span.closest('div[role="row"]') || span.closest('div[tabindex="-1"]') || span.closest('div._ak9y');
            if (row) {
                row.click();
                // Simulate mousedown too as some frameworks require it
                const event = new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window });
                row.dispatchEvent(event);
            }
            return 'clicked';
        }
    }
    return 'not_found';
})()
"@
        
        $clickResult = Send-CDPCommand $ws $clickJs
        
        if ($clickResult -ne 'clicked') {
            Write-Host "  Could not click: $clickResult" -ForegroundColor Yellow
            $failed++
            continue
        }
        
        # Wait for chat to load
        Start-Sleep -Seconds 2
        
        # Scroll up to load history (Robust)
        Write-Host "  Loading history..." -NoNewline -ForegroundColor Gray
        $scrollJs = @'
(function() {
    // 1. Find main chat container
    const containers = Array.from(document.querySelectorAll('div[tabindex="-1"]'));
    let chatDiv = containers.find(div => {
        const rect = div.getBoundingClientRect();
        const text = div.innerText || "";
        if (rect.left < 50) return false; 
        if (text.includes("Search or start a new chat") && text.length < 500) return false;
        return true; 
    });
    
    if (!chatDiv) {
        // Fallback to largest scrollable
        chatDiv = containers.sort((a,b) => (b.clientWidth * b.clientHeight) - (a.clientWidth * a.clientHeight))[0];
    }
    
    if (chatDiv) {
        if (chatDiv.scrollTop > 0) {
            const oldHeight = chatDiv.scrollHeight;
            chatDiv.scrollTop = 0; // Scroll to top
            return { scrolled: true, height: oldHeight, top: chatDiv.scrollTop };
        }
        return { scrolled: false, height: chatDiv.scrollHeight, top: chatDiv.scrollTop };
    }
    return { scrolled: false, error: 'no_container' };
})()
'@
        
        # Scroll up to 30 times or until top reached
        $maxScrolls = 30
        $lastHeight = 0
        $noChangeCount = 0
        
        for ($s = 0; $s -lt $maxScrolls; $s++) {
            $res = Send-CDPCommand $ws $scrollJs
            
            if ($res.error) { break }
            if (-not $res.scrolled) { 
                # Already at top?
                break 
            }
            
            # Wait for loading
            Start-Sleep -Seconds 2
            
            # Check if height increased (loading happened)
            # We can't easily check height change from PS side without another call, 
            # but usually wait + scroll again is enough.
            Write-Host "." -NoNewline -ForegroundColor Gray
        }
        Write-Host " Done" -ForegroundColor Gray
        
        Start-Sleep -Seconds 2
        
        Start-Sleep -Seconds 2
        # Scrape Loop (Scroll Down and Capture)
        Write-Host "  Scraping messages..." -NoNewline -ForegroundColor Gray
        
        $uniqueMsgs = @{} # Key: Timestamp+Sender+Text
        $allMsgsList = [System.Collections.Generic.List[Object]]::new()
        
        $extractJs = @'
(function() {
    const messages = [];
    
    // 1. Find the main message container (ScrollHeight Strategy)
    // We want the container with HUGE history (scrollHeight > clientHeight) on the right side.
    
    const allDivs = Array.from(document.querySelectorAll('div'));
    const candidates = allDivs.filter(div => {
        const r = div.getBoundingClientRect();
        // Right side (L > 300), Visible (H > 200), Scrollable (ScrollH > ClientH)
        // Relax ScrollH check slightly (>=)
        return r.left > 300 && r.height > 200 && div.scrollHeight > div.clientHeight;
    });
    
    // Sort by ScrollHeight (Deepest history first)
    candidates.sort((a,b) => b.scrollHeight - a.scrollHeight);
    
    let chatContainer = candidates[0];
    
    // Fallback: If no scrollable found, take largest area right-side div
    if (!chatContainer) {
         const areaCandidates = allDivs.filter(div => {
            const r = div.getBoundingClientRect();
            return r.left > 300 && r.width > 300 && r.height > 400;
        });
        areaCandidates.sort((a,b) => (b.clientWidth * b.clientHeight) - (a.clientWidth * a.clientHeight));
        chatContainer = areaCandidates[0];
    }
    
    if (!chatContainer) return { messages: [], debug: "NoContainer" };
    
    // Found container.
    const fullText = chatContainer.innerText || "";
    
    // Strategy A: Row Iteration (Existing)
    let rowMsgs = [];
    let rowParent = chatContainer;
    for (let level=0; level<5; level++) {
        if (rowParent.children.length === 1 && rowParent.firstElementChild.tagName === 'DIV') {
            rowParent = rowParent.firstElementChild;
        } else if (rowParent.children.length === 0) {
            break; 
        } else {
            break; 
        }
    }
    const rows = rowParent.children;
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const t = row.innerText?.trim() || "";
        if (!t) continue;
        
        let sender = "Them"; 
        const bubble = row.querySelector('div[style*="color"], div[class*="message-out"], div[class*="message-in"]');
        const wrapper = row.querySelector('div');
        if (wrapper) {
            const style = window.getComputedStyle(wrapper);
            if (style.justifyContent === 'flex-end' || style.alignItems === 'flex-end') sender = "Me";
        }
        if (row.innerHTML.includes('data-icon="msg-dblcheck"') || row.innerHTML.includes('data-icon="msg-check"')) sender = "Me";
        
        let timestamp = "";
        const timeMatch = t.match(/(\d{1,2}:\d{2}(?:\s?[aApP][mM])?)/);
        if (timeMatch) timestamp = timeMatch[1];
        
        // Clean text
        let cleanText = t;
        if (cleanText === timestamp) continue;
        // if (cleanText.length > 5000) continue; // Remove limitation for now
        
        rowMsgs.push({ timestamp, sender, text: cleanText });
    }
    
    // Strategy B: Raw Text Regex (Fallback if Row extraction is poor)
    // WhatsApp Copy format: [10:30, 1/1/2024] Sender: Message
    // Or just raw lines if no "Copy" format
    let regexMsgs = [];
    if (fullText.length > 100) {
        // Regex to find timestamps
        const lines = fullText.split('\n');
        let currentMsg = null;
        
        lines.forEach(line => {
            const tsMatch = line.match(/^\[?(\d{1,2}:\d{2}(?:\s?[aApP][mM])?)\]?(.*)/);
            if (tsMatch) {
                if (currentMsg) regexMsgs.push(currentMsg);
                currentMsg = { timestamp: tsMatch[1], sender: "Unknown", text: tsMatch[2].trim() };
            } else {
                if (currentMsg) currentMsg.text += "\n" + line;
                else if (line.trim().length > 0) regexMsgs.push({ timestamp: "", sender: "Unknown", text: line.trim() });
            }
        });
        if (currentMsg) regexMsgs.push(currentMsg);
    }
    
    // Decision: Use Rows if decent, else Regex
    let validMsgs = rowMsgs;
    let method = "Rows";
    
    if (rowMsgs.length < 2 && regexMsgs.length > 5) {
        validMsgs = regexMsgs;
        method = "Regex";
    }
    
    return { 
        messages: validMsgs, 
        debug: `Meth:${method} Rows:${rows.length} TxtLen:${fullText.length} Extr:${validMsgs.length} Top:${chatContainer.scrollTop}` 
    };
})()
'@

        $scrollDownJs = @'
(function() {
    // 1. Find the main message container (ScrollHeight Strategy matching extractJs)
    const allDivs = Array.from(document.querySelectorAll('div'));
    const candidates = allDivs.filter(div => {
        const r = div.getBoundingClientRect();
        return r.left > 300 && r.height > 200 && div.scrollHeight > div.clientHeight;
    });
    candidates.sort((a,b) => b.scrollHeight - a.scrollHeight);
    
    let chatDiv = candidates[0];
    
    if (!chatDiv) {
        // Fallback
        const areaCandidates = allDivs.filter(div => {
            const r = div.getBoundingClientRect();
            return r.left > 300 && r.width > 300 && r.height > 400;
        });
        areaCandidates.sort((a,b) => (b.clientWidth*b.clientHeight) - (a.clientWidth*a.clientHeight));
        chatDiv = areaCandidates[0];
    }

    if (!chatDiv) return { scrolled: false, atBottom: true, debug: "NoContainer" };
    
    // Attempt to refine if it's a wrapper (check for huge child)
    // Though usually the scrollbar is on the parent.
    // We trust ScrollHeight sorting found the right one.
    
    const prevTop = chatDiv.scrollTop;
    chatDiv.scrollTop += chatDiv.clientHeight;
    // Allow decent margin for bottom check
    const atBottom = (chatDiv.scrollTop + chatDiv.clientHeight >= chatDiv.scrollHeight - 50);
    
    return { 
        scrolled: chatDiv.scrollTop > prevTop, 
        atBottom: atBottom,
        debug: `Scroll:${prevTop}->${chatDiv.scrollTop}` 
    };
})()
'@

        $page = 0
        $maxPages = 100 # Safety limit
        
        do {
            # Extract
            $resExt = Send-CDPCommand $ws $extractJs
            $msgs = $resExt.messages
            
            # Print debug dot with info
            Write-Host " [Rows:$($resExt.debug)]" -NoNewline -ForegroundColor DarkGray
            
            if ($msgs) {
                foreach ($m in $msgs) {
                    $key = "$($m.timestamp)|$($m.sender)|$($m.text)"
                    if (-not $uniqueMsgs.ContainsKey($key)) {
                        $uniqueMsgs[$key] = $true
                        $allMsgsList.Add($m)
                    }
                }
            }
            
            # Scroll Down
            $res = Send-CDPCommand $ws $scrollDownJs
            
            Start-Sleep -Milliseconds 500
            
            $page++
        } while (-not $res.atBottom -and $page -lt $maxPages)

        
        Write-Host " Done" -ForegroundColor Gray
        
        if ($allMsgsList.Count -gt 0) {
            $csv = @("Timestamp,Sender,Message")
            foreach ($m in $allMsgsList) {
                $ts = ($m.timestamp -replace '"', '""')
                $sn = ($m.sender -replace '"', '""')
                # Replace newlines
                $tx = ($m.text -replace '[\r\n]+', ' ' -replace '"', '""')
                $csv += "`"$ts`",`"$sn`",`"$tx`""
            }
            $csv | Out-File $csvPath -Encoding utf8
            Write-Host "  Saved $($allMsgsList.Count) messages" -ForegroundColor Green
            $exported++
        }
        else {
            Write-Host "  No messages found" -ForegroundColor Yellow
            $failed++
        }
    }
    
    Write-Host "`n=== Summary ===" -ForegroundColor Cyan
    Write-Host "Exported: $exported" -ForegroundColor Green
    Write-Host "Skipped: $skipped" -ForegroundColor Yellow
    Write-Host "Failed: $failed" -ForegroundColor Red
}
catch {
    Write-Error "Error: $_"
}
finally {
    if ($ws) { $ws.Dispose() }
    if ($cts) { $cts.Dispose() }
}
