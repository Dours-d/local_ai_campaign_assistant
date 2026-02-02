<#
.SYNOPSIS
Compares Chuffed and Whydonate campaign lists to find gaps.
#>

$DataDir = Join-Path $PSScriptRoot "..\data"
$ChuffedFile = Join-Path $DataDir "chuffed_campaigns.json"
$WhydonateFile = Join-Path $DataDir "whydonate_campaigns.json"
$OutputFile = Join-Path $DataDir "migration_todo.json"

if (-not (Test-Path $ChuffedFile) -or -not (Test-Path $WhydonateFile)) {
    Write-Error "Data files not found. Please run scrape_campaigns.ps1 first or create them manually."
    exit 1
}

$ChuffedData = Get-Content $ChuffedFile | ConvertFrom-Json
$WhydonateData = Get-Content $WhydonateFile | ConvertFrom-Json

Write-Host "Loaded $($ChuffedData.Count) Chuffed campaigns."
Write-Host "Loaded $($WhydonateData.Count) Whydonate campaigns."

$ToMigrate = @()
$AlreadyMigrated = @()

foreach ($chuffed in $ChuffedData) {
    # Filter out Archived/Closed if status is present
    if ($chuffed.status -eq "archived" -or $chuffed.title -match "\(Closed\)" -or $chuffed.title -match "\[Archived\]") {
        # Skip this campaign
        continue
    }

    # Simple normalization: lowercase, remove non-alphanumeric
    $cTitle = $chuffed.title -replace '[^a-zA-Z0-9]', ''
    
    $match = $null
    foreach ($wd in $WhydonateData) {
        $wTitle = $wd.title -replace '[^a-zA-Z0-9]', ''
        # Check if title is contained in the other
        if ($cTitle -match $wTitle -or $wTitle -match $cTitle) {
            $match = $wd
            break
        }
    }
    
    if ($match) {
        $AlreadyMigrated += @{
            chuffed   = $chuffed
            whydonate = $match
        }
    }
    else {
        $ToMigrate += $chuffed
    }
}

Write-Host "`n--- Analysis Report ---"
Write-Host "Total Chuffed:     $($ChuffedData.Count)"
Write-Host "Already Migrated:  $($AlreadyMigrated.Count)"
Write-Host "Need Migration:    $($ToMigrate.Count)"

$ToMigrate | ConvertTo-Json -Depth 3 | Out-File $OutputFile -Encoding utf8
Write-Host "`nGap list saved to $OutputFile"
