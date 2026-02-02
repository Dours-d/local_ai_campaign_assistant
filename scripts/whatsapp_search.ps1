# WhatsApp Campaign Search Tool
# Searches for campaign IDs in WhatsApp Web

param(
    [string]$Port = "9222",
    [int]$StartFrom = 1
)

$scriptPath = Split-Path $PSCommandPath -Parent
$root = Split-Path $scriptPath -Parent

# Load campaigns
$checklist = Import-Csv (Join-Path $root "data/whatsapp_search_checklist.csv")
Write-Host "Loaded $($checklist.Count) campaigns to search" -ForegroundColor Cyan

# Connect to Chrome
$Tabs = Invoke-RestMethod "http://localhost:$Port/json" -ErrorAction SilentlyContinue
$WaTab = $Tabs | Where-Object { $_.url -match "web.whatsapp.com" -and $_.type -eq "page" } | Select-Object -First 1

if (-not $WaTab) {
    Write-Host "No WhatsApp Web tab found. Please open WhatsApp Web in Chrome with debugging." -ForegroundColor Red
    exit
}

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

Write-Host "`n=== WhatsApp Campaign Search ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n"

$results = @()
$count = 0

foreach ($c in $checklist | Select-Object -Skip ($StartFrom - 1)) {
    $count++
    $id = $c.search_id
    
    Write-Host "[$count] Searching: $id..." -ForegroundColor Yellow
    
    # Search in WhatsApp
    $searchJs = @"
    (async function() {
        // Find and click search box
        const searchBox = document.querySelector('[data-testid="chat-list-search"]') 
                       || document.querySelector('div[contenteditable="true"][data-tab="3"]')
                       || document.querySelector('[title="Search input textbox"]');
        
        if (!searchBox) return { error: "Search box not found" };
        
        searchBox.click();
        searchBox.focus();
        await new Promise(r => setTimeout(r, 300));
        
        // Clear and type
        document.execCommand('selectAll');
        document.execCommand('insertText', false, '$id');
        
        await new Promise(r => setTimeout(r, 2000));
        
        // Get search results
        const results = Array.from(document.querySelectorAll('[data-testid="cell-frame-container"]'))
            .map(el => {
                const title = el.querySelector('[data-testid="cell-frame-title"]');
                return title ? title.innerText : null;
            })
            .filter(t => t);
        
        return { searchedFor: '$id', results: results.slice(0, 5) };
    })()
"@
    
    $res = Send-CDP $searchJs
    $val = $res.result.result.value
    
    if ($val.error) {
        Write-Host "  Error: $($val.error)" -ForegroundColor Red
    } elseif ($val.results.Count -eq 0) {
        Write-Host "  No results found" -ForegroundColor Gray
    } else {
        Write-Host "  Found: $($val.results -join ', ')" -ForegroundColor Green
        $results += [PSCustomObject]@{
            campaign_id = $id
            whatsapp_contacts = ($val.results -join "; ")
        }
    }
    
    Start-Sleep -Seconds 1
}

# Save results
$results | Export-Csv (Join-Path $root "data/whatsapp_search_results.csv") -NoTypeInformation -Encoding UTF8
Write-Host "`nSaved results to data/whatsapp_search_results.csv"
