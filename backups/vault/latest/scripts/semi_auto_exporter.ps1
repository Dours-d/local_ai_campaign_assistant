
# Semi-Automated Bulk Exporter (Debug Version)
param(
    [string]$Port = "9222",
    [string]$ExportDir = "data\exports"
)

Write-Host "DEBUG: Script Started" -ForegroundColor DarkGray
$wshell = New-Object -ComObject WScript.Shell
if (-not $wshell) { Write-Error "Failed to create WScript.Shell"; exit }

if (-not (Test-Path $ExportDir)) { New-Item -Path $ExportDir -ItemType Directory -Force | Out-Null }

$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" -and $_.type -eq "page" } | Select-Object -First 1
if (-not $WaTab) { Write-Error "No WhatsApp tab found."; exit }

$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
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

Write-Host "=== WhatsApp Semi-Auto Exporter (DEBUG) ===" -ForegroundColor Cyan
Write-Host "Discovering chats..." 
$discoverJs = @'
(function() {
    const chats = [];
    document.querySelectorAll('span[title]').forEach(span => {
        const title = span.title.trim();
        if (title.length > 1 && title.length < 80 && 
            !['Search','Settings','New chat','Status','Menu','Archived','Filter chats','Community', 'Unread', 'All'].includes(title) &&
            !title.match(/^\d{1,2}:\d{2}/)) {
            chats.push(title);
        }
    });
    return [...new Set(chats)];
})()
'@
$res = Send-CDP $discoverJs
$chatList = $res.result.result.value
Write-Host "Found $($chatList.Count) chats." -ForegroundColor Green

foreach ($chatName in $chatList) {
    if ($chatName -match "Lawyer Nizar") {
        # Debug: force run on Lawyer Nizar even if exists
    }
    else {
        # Standard skip logic
        $safeName = $chatName -replace '[^\w\s-]', '' -replace '\s+', '_'
        if (-not $safeName) { $safeName = "Unknown" }
        $path = Join-Path $ExportDir "$safeName.txt"
        if (Test-Path $path) { if ((Get-Item $path).Length -gt 100) { continue } }
    }
    
    $safeName = $chatName -replace '[^\w\s-]', '' -replace '\s+', '_'
    $path = Join-Path $ExportDir "$safeName.txt"

    Write-Host "`nOpening: $chatName" -ForegroundColor Cyan
    
    $clickJs = @"
(function() {
    const spans = document.querySelectorAll('span[title]');
    for (const span of spans) {
        if (span.title === `"$($chatName -replace '"', '\"')`") {
            span.click();
            const row = span.closest('div[role="row"]') || span.closest('div._ak9y');
            if (row) {
                const event = new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window });
                row.dispatchEvent(event);
            }
            return 'clicked';
        }
    }
    return 'not_found';
})()
"@
    $clickRes = Send-CDP $clickJs
    
    Write-Host "ACTION: 1. Scroll Up   2. Click in Chat   3. Press ENTER here" -ForegroundColor Yellow
    $userInput = Read-Host "Press ENTER"
    if ($userInput -eq 's') { continue }
    
    Write-Host "Exporting in 3 seconds... (FOCUS BROWSER)"
    Start-Sleep -Seconds 3
    
    try {
        Write-Host "DEBUG: Sending Ctrl+A..." -ForegroundColor DarkGray
        $wshell.SendKeys("^a")
        Start-Sleep -Milliseconds 500
        
        Write-Host "DEBUG: Sending Ctrl+C..." -ForegroundColor DarkGray
        $wshell.SendKeys("^c")
        Start-Sleep -Milliseconds 1500 
        
        Write-Host "DEBUG: Getting Clipboard..." -ForegroundColor DarkGray
        $text = Get-Clipboard | Out-String
        if ($text) { $text = $text.Trim() }
        
        Write-Host "DEBUG: Clipboard length: $(if ($text) { $text.Length } else { 'NULL' })" -ForegroundColor DarkGray
        
        if (-not $text -or $text.Length -lt 10) {
            Write-Warning " - Clipboard empty/small. Retrying Copy..."
            $wshell.SendKeys("^c")
            Start-Sleep -Milliseconds 1000
            $text = Get-Clipboard | Out-String
        }
        
        if ($text.Length -gt 10) {
            $text | Set-Content -Path $path -Encoding utf8
            Write-Host " - Saved $(($text.Length)) chars" -ForegroundColor Green
            Set-Clipboard " "
        }
        else {
            Write-Error " - Failed to capture text."
        }
            
    }
    catch {
        Write-Error " - CRASH: $_"
    }
}
Write-Host "`nDone." -ForegroundColor Green
