
# WhatsApp + Campaigns Rationality Auditor
# Compiles all JSON data into a single CSV for visual inspection

param(
    [string]$ExportDir = "data/exports",
    [string]$UnifiedJson = "data/campaigns_unified.json",
    [string]$OutputRoot = "data/rationality_audit"
)

# 1. Compile WhatsApp Summary
Write-Host "Compiling WhatsApp Export Summary..." -ForegroundColor Cyan
$waFiles = Get-ChildItem -Path $ExportDir -Filter "*.json"
$waSummary = foreach ($file in $waFiles) {
    try {
        $data = Get-Content -Path $file.FullName | ConvertFrom-Json
        $msgCount = $data.Count
        if ($null -eq $msgCount) { $msgCount = 0 }
        
        $lastMsg = ""
        $lastDate = ""
        if ($msgCount -gt 0) {
            $last = $data[-1]
            $lastMsg = $last.text -replace "`n", " " -replace "`r", ""
            $lastDate = $last.timestamp
        }
        
        [PSCustomObject]@{
            Source      = "WhatsApp"
            Category    = "Interactions"
            Identifier  = $file.BaseName
            Status      = "Exported"
            Metric      = $msgCount
            MetricLabel = "Messages"
            LastDate    = $lastDate
            Snippet     = $lastMsg
        }
    }
    catch {
        Write-Warning "Skipped $($file.Name): $($_.Exception.Message)"
    }
}

# 2. Compile Unified Campaigns Summary
Write-Host "Compiling Campaigns Summary..." -ForegroundColor Cyan
if (Test-Path $UnifiedJson) {
    $db = Get-Content -Path $UnifiedJson | ConvertFrom-Json
    $campaignSummary = foreach ($c in $db.campaigns) {
        [PSCustomObject]@{
            Source      = "Campaign"
            Category    = $c.platform
            Identifier  = $c.privacy.display_name
            Status      = $c.status
            Metric      = $c.raised_eur
            MetricLabel = "EUR Raised"
            LastDate    = $c.attention.last_activity
            Snippet     = $c.title
        }
    }
}

# 3. Join and Export
Write-Host "Generating Master Audit Sheet..." -ForegroundColor Green
$allData = $waSummary + $campaignSummary
$outputPath = "$OutputRoot.csv"
$allData | Export-Csv -Path $outputPath -NoTypeInformation -Encoding utf8

Write-Host "`nRationality Audit Sheet generated: $outputPath" -ForegroundColor Cyan
Write-Host "Total Records: $($allData.Count)"
