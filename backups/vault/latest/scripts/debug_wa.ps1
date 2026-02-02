$Tabs = Invoke-RestMethod 'http://localhost:9222/json'
$WaTab = $Tabs | Where-Object { $_.url -match 'whatsapp' } | Select-Object -First 1
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$ws.ConnectAsync([Uri]$WaTab.webSocketDebuggerUrl, [System.Threading.CancellationToken]::None).Wait()

$js = @"
(function() {
    return {
        totalElements: document.querySelectorAll('*').length,
        documentTitle: document.title,
        readyState: document.readyState,
        textSnippet: document.body.innerText.substring(0, 200),
        first10Roles: Array.from(document.querySelectorAll('[role]')).slice(0, 10).map(e => e.getAttribute('role'))
    };
})()
"@

$payload = @{ id = 1; method = 'Runtime.evaluate'; params = @{ expression = $js; returnByValue = $true } } | ConvertTo-Json -Compress
$bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
$ws.SendAsync([ArraySegment[byte]]::new($bytes), 1, $true, [System.Threading.CancellationToken]::None).Wait()

$buf = [byte[]]::new(1MB); $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), [System.Threading.CancellationToken]::None); $res.Wait()
$json = [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count)
$ws.Dispose()
$json
