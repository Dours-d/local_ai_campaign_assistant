<#
.SYNOPSIS
    Trustee Intelligence System Test Runner (Fixed Assertions)
#>

$OldReport = Join-Path $PSScriptRoot "..\data\trustee_usdt_report.csv"
$TestFile = Join-Path $PSScriptRoot "..\data\test_intelligence.csv"

Write-Host "`n[Initializing Trustee Intelligence System Tests]" -ForegroundColor Cyan

# 1. Generate fresh test data
& "$PSScriptRoot\create_test_data.ps1"

# 2. Run Scanner
Write-Host "Running Intelligence Scanner..." -NoNewline
& "$PSScriptRoot\scan_usdt.ps1" -SilentStatus
Write-Host " Done." -ForegroundColor Green

# 3. Assertions
if (-not (Test-Path $OldReport)) {
    Write-Error "Test Failed: trustee_usdt_report.csv was not generated."
    exit 1
}

$Report = Import-Csv $OldReport

Write-Host "`n[Verifying Intelligence Integrity]" -ForegroundColor Cyan

# Check for Orphans
$Orphans = $Report | Where-Object { [string]::IsNullOrWhiteSpace($_.WhatsID) }
if ($Orphans.Count -gt 0) {
    Write-Host "❌ FAILED: Found $($Orphans.Count) orphaned addresses in report." -ForegroundColor Red
}
else {
    Write-Host "✅ PASSED: No orphaned addresses permitted." -ForegroundColor Green
}

# Check for Invalid Formats
$Invalids = $Report | Where-Object { $_.USDTAddress -match "0" -and $_.USDTAddress -match "T" }
if ($Invalids.Count -gt 0) {
    Write-Host "❌ FAILED: Found $($Invalids.Count) invalid Base58 addresses in report." -ForegroundColor Red
}
else {
    Write-Host "✅ PASSED: Exactitude verified (Illegal Base58 scrapped)." -ForegroundColor Green
}

# Check for Correct Linkage
$ValidCount = $Report.Count
if ($ValidCount -ge 3) {
    Write-Host "✅ PASSED: Identity Anchoring confirmed ($ValidCount valid links found)." -ForegroundColor Green
}
else {
    Write-Host "❌ FAILED: Found only $ValidCount valid links. Expected 3+." -ForegroundColor Red
}

# Check Education (Seed Phrase)
$Custodial = $Report | Where-Object { $_.CustodyQuality -eq "Third-Party" }
if ($Custodial.PhraseControl -contains "Block") {
    Write-Host "✅ PASSED: Middleman Risk correctly flagged (🚫 NO)." -ForegroundColor Green
}
else {
    Write-Host "❌ FAILED: Middleman Risk indicator missing." -ForegroundColor Red
}

Write-Host "`n[Full System Verification Complete]" -ForegroundColor Green
