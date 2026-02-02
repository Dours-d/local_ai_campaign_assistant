<#
.SYNOPSIS
Scrapes campaign titles from Chuffed and Whydonate public profile URLs using regex or embedded JSON.

.DESCRIPTION
Usage:
    .\scripts\scrape_campaigns.ps1 -ChuffedUrl "https://chuffed.org/project/..." -WhydonateUrl "https://whydonate.nl/..."

Outputs:
    data/chuffed_campaigns.json
    data/whydonate_campaigns.json
#>

param (
    [string]$ChuffedUrl = "https://chuffed.org/search/fajr", 
    [string]$WhydonateUrl = "https://whydonate.nl/en/search/fajr" 
)

$DataDir = Join-Path $PSScriptRoot "..\data"
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir | Out-Null }

function Scrape-Chuffed {
    param ($Url)
    
    $LocalFile = Join-Path $DataDir "chuffed_dashboard.html"
    
    if (Test-Path $LocalFile) {
        Write-Host "Parsing local Chuffed dashboard: $LocalFile"
        $Content = Get-Content $LocalFile -Raw
        
        # Robust extraction: found 'window.Chuffed.dashboardInit = { ... }' in HTML
        # Using (?s) to allow matching across newlines
        if ($Content -match '(?s)window\.Chuffed\.dashboardInit\s*=\s*(\{.*?\});') {
            $JsonBlob = $matches[1]
            try {
                $DashboardData = $JsonBlob | ConvertFrom-Json
                
                $Campaigns = @()
                if ($DashboardData.campaigns -and $DashboardData.campaigns.items) {
                    foreach ($item in $DashboardData.campaigns.items) {
                        # Filter: "redacted" and "live" statuses only
                        # User wants primarily redacted campaigns migrated, but capturing live context helps.
                        if ($item.status -in @("redacted", "live")) {
                            $Campaigns += @{
                                id         = $item.id
                                title      = $item.title
                                slug       = $item.slug
                                url        = "https://chuffed.org/project/" + $item.slug
                                source     = "chuffed"
                                status     = $item.status
                                raised     = $item.amount
                                currency   = $item.currency
                                image      = $item.image
                                created_at = $item.created_at
                            }
                        }
                    }
                }
                
                $Unique = $Campaigns | Sort-Object url -Unique
                $JsonPath = Join-Path $DataDir "chuffed_campaigns.json"
                $Unique | ConvertTo-Json -Depth 5 | Out-File $JsonPath -Encoding utf8
                Write-Host "Saved $($Unique.Count) Chuffed campaigns to $JsonPath (via JSON)"
                return
            }
            catch {
                Write-Warning "JSON parsing failed: $_. Falling back to regex..."
            }
        }
    }
    else {
        Write-Host "Scraping Chuffed URL: $Url"
        try {
            $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing
            $Content = $Response.Content
        }
        catch {
            Write-Error "Failed to scrape Chuffed URL and no local file found: $_"
            return
        }
    }

    try {
        $Campaigns = @()
        
        # Fallback Old Regex
        $regex = [regex] '<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        
        $LinkMatches = $regex.Matches($Content)
        foreach ($match in $LinkMatches) {
            $link = $match.Groups[1].Value
            $title = $match.Groups[2].Value.Trim()
            
            if ($link -like "*chuffed.org/project/*") {
                $Campaigns += @{
                    title  = $title
                    url    = $link
                    source = "chuffed"
                    status = "active" 
                }
            }
        }
        
        $Unique = $Campaigns | Sort-Object url -Unique
        
        $JsonPath = Join-Path $DataDir "chuffed_campaigns.json"
        $Unique | ConvertTo-Json -Depth 2 | Out-File $JsonPath -Encoding utf8
        Write-Host "Saved $($Unique.Count) Chuffed campaigns to $JsonPath (Fallback)"
    }
    catch {
        Write-Error "Failed to parse Chuffed data: $_"
    }
}

function Scrape-Whydonate {
    param ($Url)
    Write-Host "Scraping Whydonate: $Url"
    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing
        
        $Campaigns = @()
        
        # Simple Regex Fallback
        $regex = [regex] 'href="\/fundraising\/([^"]+)"'
        $matches = $regex.Matches($Response.Content)
        
        foreach ($match in $matches) {
            $slug = $match.Groups[1].Value
            $Campaigns += @{
                title  = $slug 
                url    = "https://whydonate.nl/fundraising/$slug"
                source = "whydonate"
            }
        }

        $Unique = $Campaigns | Sort-Object url -Unique
        
        $JsonPath = Join-Path $DataDir "whydonate_campaigns.json"
        $Unique | ConvertTo-Json -Depth 2 | Out-File $JsonPath -Encoding utf8
        Write-Host "Saved $($Unique.Count) Whydonate campaigns to $JsonPath"
    }
    catch {
        Write-Error "Failed to scrape Whydonate: $_"
    }
}

Scrape-Chuffed -Url $ChuffedUrl
Scrape-Whydonate -Url $WhydonateUrl
