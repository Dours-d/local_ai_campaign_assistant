
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

# Dump classes of deep elements
$js = @'
(function() {
    // Find deep elements that might be messages
    const deep = document.querySelectorAll('div > span > span'); 
    const classes = new Count();
    
    function traverse(node, depth) {
        if (depth > 10) return;
        if (node.classList && node.classList.length > 0) {
            node.classList.forEach(c => {
                 // collect common classes
            });
        }
        // ...
    }
    
    // Just get the HTML of the main container if possible
    const main = document.querySelector('div[role="application"]') || document.body;
    return main.innerText.substring(0, 2000); // Get text to see if we can see messages
})()
'@

# Simpler: Get class names of elements containing text "Hello" or common words?
# Or just dump the HTML of a probable message container
$js_dump = @'
(function() {
    const bubbles = document.querySelectorAll('div[data-testid^="msg-"]');
    if (bubbles.length > 0) {
        return "Found bubbles: " + bubbles.length + " | HTML: " + bubbles[0].outerHTML;
    }
    
    // Try finding by text content
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    const samples = [];
    while(node = walker.nextNode()) {
        if (node.parentElement.tagName === 'SPAN' && node.textContent.length > 20) {
            samples.push({
                text: node.textContent.substring(0, 50), 
                classes: node.parentElement.className,
                parentClasses: node.parentElement.parentElement.className
            });
            if (samples.length > 5) break;
        }
    }
    return samples;
})()
'@

$res = Send-CDP $js_dump
Write-Host "Inspector Result:" -ForegroundColor Cyan
$res.result.result.value | Format-List
