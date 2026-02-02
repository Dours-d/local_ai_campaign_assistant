<#
.SYNOPSIS
    WhatsApp Local Usage Extractor (Identity-Aware CSV Edition)
    Connects to an active browser session to "listen" for messages with full Chain of Custody.
#>

param (
    [string]$Port = "9222",
    [string]$OutputFile = "data\whatsapp_live_extract.csv",
    [bool]$AutoScan = $true,
    [bool]$Continuous = $true,
    [bool]$AutoScroll = $false,
    [int]$IntervalSeconds = 30,
    [string]$ChatTitle = ""
)

# Function to send/receive via WebSocket
function Invoke-CDPCommand {
    param (
        [string]$Url,
        [string]$Method,
        [hashtable]$Params = @{}
    )

    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $ct = [System.Threading.CancellationTokenSource]::new()
    $uri = [System.Uri]::new($Url)
    
    try {
        $task = $ws.ConnectAsync($uri, $ct.Token)
        $task.Wait()

        $id = Get-Random
        $payload = @{
            id     = $id
            method = $method
            params = $params
        } | ConvertTo-Json

        $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
        $segment = [System.ArraySegment[byte]]::new($bytes)
        
        $sendTask = $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct.Token)
        $sendTask.Wait()

        $buffer = [byte[]]::new(1024000) # 1MB buffer for larger history
        $receiveSegment = [System.ArraySegment[byte]]::new($buffer)
        $receiveTask = $ws.ReceiveAsync($receiveSegment, $ct.Token)
        $receiveTask.Wait()

        $responseJson = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $receiveTask.Result.Count)
        $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Done", $ct.Token).Wait()
        
        return $responseJson | ConvertFrom-Json
    }
    catch {
        Write-Warning "CDP Error: $_"
        return $null
    }
}

# Ensure data directory exists
if (-not (Test-Path -Path "data")) { New-Item -Path "data" -ItemType Directory }

# Initialize CSV if it doesn't exist
if (-not (Test-Path $OutputFile)) {
    "Timestamp,PhoneNumber,WhatsID,Sender,Message,ChatName" | Out-File -FilePath $OutputFile -Encoding utf8
}

Write-Host "`n[WhatsApp Identity-Aware Extractor]" -ForegroundColor Cyan
Write-Host "Monitoring browser on port $Port for strict Chain of Custody."
Write-Host "Output: $OutputFile`n"

$Global:LastExtractionData = ""

while ($true) {
    try {
        $TabsUrl = "http://localhost:$Port/json"
        $Tabs = Invoke-RestMethod -Uri $TabsUrl
        
        if ($Tabs) {
            $WaTab = $null
            if ($ChatTitle) {
                $WaTab = $Tabs | Where-Object { $_.url -match "web.whatsapp.com" -and $_.title -match $ChatTitle } | Select-Object -First 1
            }
            else {
                $WaTab = $Tabs | Where-Object { $_.url -match "web.whatsapp.com" } | Select-Object -First 1
            }

            if ($WaTab) {
                $WsUrl = $WaTab.webSocketDebuggerUrl
            
                # Extraction Script (Matches Bulk Exporter Schema)
                $JsCode = @"
                (function() {
                    let results = [];
                    document.querySelectorAll('div.copyable-text').forEach(el => {
                        let meta = el.getAttribute('data-pre-plain-text'); 
                        let body = el.innerText.trim();
                        let idMatch = el.closest('div[data-id]')?.getAttribute('data-id') || ''; 
                        
                        if (meta && body) {
                            let whatsId = idMatch.split('_')[1] || '';
                            let phone = whatsId.split('@')[0] || '';
                            let chatName = document.querySelector('#main header span[title]')?.getAttribute('title') || '';

                            results.push({
                                Timestamp: meta.split(']')[0].replace('[',''),
                                Sender: meta.split(']')[1].split(':')[0].trim(),
                                Message: body.replace(/"/g, '""'), # Escape quotes for CSV
                                PhoneNumber: phone,
                                WhatsID: whatsId,
                                ChatName: chatName
                            });
                        }
                    });

                    if (window.AutoScrollEnabled) {
                        let container = document.querySelector('#main div[role="region"]') || 
                                        document.querySelector('div.copyable-area')?.parentElement;
                        if (container) container.scrollTop -= 800;
                    }

                    return results;
                })()
"@

                # Set AutoScroll state
                $InitJs = "window.AutoScrollEnabled = $(if ($AutoScroll) { 'true' } else { 'false' });"
                Invoke-CDPCommand -Url $WsUrl -Method "Runtime.evaluate" -Params @{ expression = $InitJs } | Out-Null

                $Response = Invoke-CDPCommand -Url $WsUrl -Method "Runtime.evaluate" -Params @{ expression = $JsCode; returnByValue = $true }
                $Messages = $Response.result.result.value

                if ($Messages -and $Messages.Count -gt 0) {
                    $NewRows = @()
                    foreach ($msg in $Messages) {
                        $RowStr = "`"$($msg.Timestamp)`",`"$($msg.PhoneNumber)`",`"$($msg.WhatsID)`",`"$($msg.Sender)`",`"$($msg.Message)`",`"$($msg.ChatName)`""
                        $NewRows += $RowStr
                    }

                    # Deduplication: Compare the whole block to see if anything is new
                    $CurrentDataStr = $NewRows -join "`n"
                    if ($CurrentDataStr -ne $Global:LastExtractionData) {
                        # We append only the messages that aren't already represented in the hash if we wanted to be fancy, 
                        # but for now, simple block deduplication vs previous run.
                        $NewRows | Out-File -FilePath $OutputFile -Append -Encoding utf8
                        Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Captured $($Messages.Count) messages with identity anchors." -ForegroundColor Green
                        
                        if ($AutoScan) {
                            $ScanScript = Join-Path $PSScriptRoot "scan_usdt.ps1"
                            if (Test-Path $ScanScript) { & $ScanScript -SilentStatus }
                        }
                        $Global:LastExtractionData = $CurrentDataStr
                    }
                    else {
                        Write-Host "." -NoNewline # Heartbeat
                    }
                }
            }
            else { Write-Warning "Waiting for WhatsApp tab..." }
        }
    }
    catch {
        Write-Host "!" -NoNewline
    }

    if (-not $Continuous) { break }
    Start-Sleep -Seconds $IntervalSeconds
}
