# Test WhatsApp search with keyboard simulation

param([string]$Port = "9222", [string]$SearchId = "143387")

$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$WaTab = $Tabs | Where-Object { $_.url -match "web.whatsapp.com" -and $_.type -eq "page" } | Select-Object -First 1
if (-not $WaTab) { Write-Host "No WhatsApp tab found" -ForegroundColor Red; exit }

$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
$ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, $cts.Token).Wait()

function Send-CDP {
    param([string]$method = "Runtime.evaluate", [hashtable]$params)
    if ($null -eq $params -and ($method -match "\s" -or $method -match "\(")) {
        $params = @{ expression = $method; returnByValue = $true; awaitPromise = $true }
        $method = "Runtime.evaluate"
    }
    $msg = @{ id = Get-Random; method = $method; params = $params } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    
    $allBytes = New-Object System.Collections.Generic.List[byte]
    $buffer = [byte[]]::new(65536)
    do {
        $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cts.Token).Result
        if ($res.Count -gt 0) { 
            $slice = [byte[]]$buffer[0..($res.Count - 1)]
            $allBytes.AddRange($slice) 
        }
    } while (-not $res.EndOfMessage)
    
    return [System.Text.Encoding]::UTF8.GetString($allBytes.ToArray()) | ConvertFrom-Json
}

Write-Host "Searching WhatsApp for: $SearchId" -ForegroundColor Cyan

# Step 1: Focus the search box
$focusJs = @"
(function() {
    const searchBox = document.querySelector('div[contenteditable="true"][data-tab="3"]')
                   || document.querySelector('div[contenteditable="true"]');
    if (searchBox) {
        searchBox.click();
        searchBox.focus();
        return { focused: true };
    }
    return { focused: false };
})()
"@

$focusRes = Send-CDP $focusJs
Write-Host "Focus: $($focusRes.result.result.value | ConvertTo-Json -Compress)"

Start-Sleep -Milliseconds 500

# Step 2: Clear with Ctrl+A, Backspace
Write-Host "Clearing..."
Send-CDP -method "Input.dispatchKeyEvent" -params @{ type = "keyDown"; key = "a"; code = "KeyA"; modifiers = 2 } | Out-Null
Send-CDP -method "Input.dispatchKeyEvent" -params @{ type = "keyUp"; key = "a"; code = "KeyA" } | Out-Null
Send-CDP -method "Input.dispatchKeyEvent" -params @{ type = "keyDown"; key = "Backspace"; code = "Backspace" } | Out-Null
Send-CDP -method "Input.dispatchKeyEvent" -params @{ type = "keyUp"; key = "Backspace"; code = "Backspace" } | Out-Null

Start-Sleep -Milliseconds 300

# Step 3: Type using insertText
Write-Host "Typing: $SearchId"
Send-CDP -method "Input.insertText" -params @{ text = $SearchId } | Out-Null

Start-Sleep -Seconds 3

# Step 4: Check results
$checkJs = @"
(function() {
    // Get current search value
    const searchBox = document.querySelector('div[contenteditable="true"][data-tab="3"]')
                   || document.querySelector('div[contenteditable="true"]');
    const searchValue = searchBox ? searchBox.innerText : 'not found';
    
    // Get visible chats/results
    const chatItems = document.querySelectorAll('[data-testid="cell-frame-container"]');
    const results = [];
    chatItems.forEach(item => {
        const titleEl = item.querySelector('span[title]') || item.querySelector('[data-testid="cell-frame-title"]');
        if (titleEl) results.push(titleEl.getAttribute('title') || titleEl.innerText);
    });
    
    // Also check for conversation list
    const convos = document.querySelectorAll('[data-testid="conversation-info-header-chat-title"]');
    convos.forEach(c => results.push('Conv: ' + c.innerText));
    
    return {
        searchValue: searchValue.trim(),
        resultsCount: chatItems.length,
        results: results.slice(0, 10)
    };
})()
"@

$checkRes = Send-CDP $checkJs
$val = $checkRes.result.result.value

Write-Host "`nSearch value in box: '$($val.searchValue)'"
Write-Host "Chat items visible: $($val.resultsCount)"
Write-Host "`nResults:"
if ($val.results.Count -gt 0) {
    $val.results | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host "  No results"
}
