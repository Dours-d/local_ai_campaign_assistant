
param([string]$Port = "9222")

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
    $buf = [byte[]]::new(1MB)
    $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), $cts.Token)
    $res.Wait()
    return [System.Text.Encoding]::UTF8.GetString($buf, 0, $res.Result.Count) | ConvertFrom-Json
}

Write-Host "Checking Menu Options..."
$js = @'
(async function() {
    // 1. Find Menu button (3 dots) in the active chat header
    // Header is usually the right pane top bar
    const header = document.querySelector('header'); 
    if (!header) return "No Header found. Open a chat first.";
    
    const menuBtn = header.querySelector('div[role="button"][title="Menu"], div[role="button"][aria-label="Menu"]');
    if (!menuBtn) return "No Menu button found. Selectors might be wrong.";
    
    // Click it
    menuBtn.click();
    
    // Wait a bit for menu to open (simulated via sleep in caller, but we can try wait here if async allowed in CDP - basic CDP eval is sync usually, need await)
    // We return state "Clicked", then caller waits and asks for menu items.
    return "Clicked Menu";
})()
'@

$res = Send-CDP $js
Write-Host "Result: $($res.result.result.value)"

Start-Sleep -Seconds 1

$js_read = @'
(function() {
    // Look for dropdown menu
    const menu = document.querySelector('div[role="application"] ul, div[role="menu"]'); // WhatsApp uses ul/li in a specific wrapper often
    if (!menu) {
        // Fallback: finding text in the DOM appearing just now
         const items = Array.from(document.querySelectorAll('li div[role="button"]')).map(el => el.innerText);
         if (items.length > 0) return items;
         return "No menu found";
    }
    
    return Array.from(menu.querySelectorAll('li')).map(li => li.innerText);
})()
'@

$res2 = Send-CDP $js_read
Write-Host "Menu Items found:" -ForegroundColor Cyan
$res2.result.result.value | Format-List
