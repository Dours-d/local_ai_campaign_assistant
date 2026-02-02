<#
.SYNOPSIS
    Simple WhatsApp chat list discovery test
#>

param([string]$Port = "9222")

$Tabs = Invoke-RestMethod "http://localhost:$Port/json"
$WaTab = $Tabs | Where-Object { $_.url -match "whatsapp" -and $_.type -eq "page" } | Select-Object -First 1

if (-not $WaTab) {
    Write-Error "No WhatsApp page found"
    exit 1
}

Write-Host "Tab: $($WaTab.title)" -ForegroundColor Green

$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = New-Object System.Threading.CancellationTokenSource
$cts.CancelAfter(30000)  # 30 second timeout

try {
    $ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, $cts.Token).Wait()
    Write-Host "Connected to WebSocket" -ForegroundColor Green
    
    # Simple JS to count elements  
    $js = 'document.querySelectorAll("span[title]").length'
    $msg = @{ id = 1; method = "Runtime.evaluate"; params = @{ expression = $js; returnByValue = $true } } | ConvertTo-Json -Compress
    
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, $cts.Token).Wait()
    Write-Host "Sent command" -ForegroundColor Green
    
    $buf = [byte[]]::new(65536)
    $segment = [ArraySegment[byte]]::new($buf)
    $result = $ws.ReceiveAsync($segment, $cts.Token)
    $result.Wait()
    
    $response = [System.Text.Encoding]::UTF8.GetString($buf, 0, $result.Result.Count)
    Write-Host "Response: $response" -ForegroundColor Cyan
    
    $json = $response | ConvertFrom-Json
    Write-Host "`nSpan elements with title: $($json.result.result.value)" -ForegroundColor Yellow
    
    # Now get actual titles
    $js2 = 'Array.from(document.querySelectorAll("span[title]")).slice(0,20).map(s => s.title)'
    $msg2 = @{ id = 2; method = "Runtime.evaluate"; params = @{ expression = $js2; returnByValue = $true } } | ConvertTo-Json -Compress
    $bytes2 = [System.Text.Encoding]::UTF8.GetBytes($msg2)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes2), 'Text', $true, $cts.Token).Wait()
    
    $buf2 = [byte[]]::new(65536)
    $result2 = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf2), $cts.Token)
    $result2.Wait()
    
    $response2 = [System.Text.Encoding]::UTF8.GetString($buf2, 0, $result2.Result.Count)
    $json2 = $response2 | ConvertFrom-Json
    
    Write-Host "`nFirst 20 titles:" -ForegroundColor Yellow
    $json2.result.result.value | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
}
catch {
    Write-Error "Error: $_"
}
finally {
    $ws.Dispose()
    $cts.Dispose()
}
