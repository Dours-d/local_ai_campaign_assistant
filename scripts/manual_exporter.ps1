
# Manual Export Helper
# Usage:
# 1. Run this script.
# 2. It will detect the WhatsApp window (via active focus or user prompt).
# 3. It will wait for you to open a chat.
# 4. It will send Ctrl+A, Ctrl+C to copy the text.
# 5. It will save the clipboard content to a file.

Add-Type -AssemblyName System.Windows.Forms

$ExportDir = "data\exports"
if (-not (Test-Path $ExportDir)) { New-Item -Path $ExportDir -ItemType Directory -Force | Out-Null }

Write-Host "=== WhatsApp Manual Exporter ===" -ForegroundColor Cyan
Write-Host "1. Open WhatsApp Web in your browser."
Write-Host "2. Click on the chat you want to export."
Write-Host "3. Make sure the chat history is loaded (scroll up if needed)."
Write-Host "4. Press ENTER here when ready to export the CURRENT visible chat." -ForegroundColor Yellow
Read-Host "Press ENTER"

# Wait a second to switch focus if needed (User should have browser focused)
Write-Host "Exporting in 3 seconds... (Click the browser window!)" -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Send Ctrl+A (Select All)
Write-Host "Selecting text..."
[System.Windows.Forms.SendKeys]::SendWait("^a")
Start-Sleep -Milliseconds 500

# Send Ctrl+C (Copy)
Write-Host "Copying..."
[System.Windows.Forms.SendKeys]::SendWait("^c")
Start-Sleep -Milliseconds 1000

# Read Clipboard
$text = [System.Windows.Forms.Clipboard]::GetText()

if (-not $text -or $text.Length -lt 10) {
    Write-Warning "Clipboard empty or too short. Did the copy work?"
    exit
}

Write-Host "Captured $($text.Length) characters." -ForegroundColor Green

# Heuristic to find Chat Name (first line or frequent name?)
# For now, ask user or use timestamp
$filename = Read-Host "Enter filename for this export (e.g. 'Malik')"
$safeName = $filename -replace '[^\w\s-]', '' -replace '\s+', '_'
$path = Join-Path $ExportDir "$safeName.txt"

$text | Out-File $path -Encoding utf8
Write-Host "Saved to $path" -ForegroundColor Green

# Parse Test (Preview)
$lines = $text -split "`n"
$msgCount = ($lines | Select-String "\[?\d{1,2}:\d{2}").Count
Write-Host "Estimated messages: $msgCount" -ForegroundColor Cyan
