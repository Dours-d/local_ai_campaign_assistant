# Campaign Database Query Tool
# Interactive explorer for campaigns, contacts, and communications

param(
    [string]$Command,
    [string]$Query,
    [string]$Filter,
    [switch]$Export
)

$script:DataPath = Join-Path $PSScriptRoot "..\data"

# Load data
function Load-Data {
    $script:ChuffedCoupling = Import-Csv (Join-Path $DataPath "coupling_vetting.csv")
    $script:WhydonateCoupling = Import-Csv (Join-Path $DataPath "whydonate_coupling_vetting.csv")
    $script:VettingList = Import-Csv (Join-Path $DataPath "vetting_checklist.csv")
    
    # Try to load unified campaigns for amounts
    $unifiedPath = Join-Path $DataPath "campaigns_unified.json"
    if (Test-Path $unifiedPath) {
        $script:UnifiedCampaigns = (Get-Content $unifiedPath -Raw | ConvertFrom-Json).campaigns
    }
    
    # Build contact index
    $script:ContactIndex = @{}
    foreach ($v in $VettingList) {
        $ContactIndex[$v.number] = $v
    }
    
    # Build campaign amount index from unified
    $script:AmountIndex = @{}
    if ($UnifiedCampaigns) {
        foreach ($c in $UnifiedCampaigns) {
            $AmountIndex[$c.id] = $c.raised_eur
        }
    }
    
    Write-Host "Loaded: $($ChuffedCoupling.Count) Chuffed, $($WhydonateCoupling.Count) Whydonate, $($VettingList.Count) Contacts" -ForegroundColor Green
}

# Search campaigns by beneficiary name
function Search-Campaign {
    param([string]$Name)
    
    $results = @()
    
    # Search Chuffed
    $results += $ChuffedCoupling | Where-Object { 
        $_.beneficiary -like "*$Name*" -or $_.title -like "*$Name*" -or $_.whatsapp_contact -like "*$Name*"
    } | ForEach-Object {
        [PSCustomObject]@{
            Platform    = "Chuffed"
            ID          = $_.chuffed_id
            Beneficiary = $_.beneficiary
            Contact     = $_.whatsapp_contact
            Number      = $_.number
            Title       = $_.title
        }
    }
    
    # Search Whydonate
    $results += $WhydonateCoupling | Where-Object {
        $_.beneficiary -like "*$Name*" -or $_.whydonate_title -like "*$Name*" -or $_.whatsapp_contact -like "*$Name*"
    } | ForEach-Object {
        [PSCustomObject]@{
            Platform    = "Whydonate"
            ID          = ""
            Beneficiary = $_.beneficiary
            Contact     = $_.whatsapp_contact
            Number      = $_.number
            Title       = $_.whydonate_title
        }
    }
    
    return $results
}

# Get contact details by phone number
function Get-Contact {
    param([string]$Number)
    
    $contact = $VettingList | Where-Object { $_.number -eq $Number }
    if (-not $contact) {
        Write-Host "Contact not found: $Number" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== Contact: $($contact.whatsapp_contact) ===" -ForegroundColor Cyan
    Write-Host "Number: $($contact.number)"
    Write-Host "Campaigns: $($contact.campaign_count)"
    Write-Host "Platforms: $($contact.platforms)"
    Write-Host "Beneficiaries: $($contact.beneficiaries)"
    Write-Host "Vetted: $($contact.vetted)"
    
    # List their campaigns
    Write-Host "`nCampaigns managed:" -ForegroundColor Yellow
    
    $ChuffedCoupling | Where-Object { $_.number -eq $Number } | ForEach-Object {
        Write-Host "  [Chuffed] $($_.beneficiary): $($_.title.Substring(0, [Math]::Min(50, $_.title.Length)))..."
    }
    
    $WhydonateCoupling | Where-Object { $_.number -eq $Number } | ForEach-Object {
        Write-Host "  [Whydonate] $($_.beneficiary): $($_.whydonate_title.Substring(0, [Math]::Min(50, $_.whydonate_title.Length)))..."
    }
}

# Get all campaigns for a beneficiary
function Get-Beneficiary {
    param([string]$Name)
    
    $campaigns = Search-Campaign -Name $Name
    
    if ($campaigns.Count -eq 0) {
        Write-Host "No campaigns found for: $Name" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== Campaigns for '$Name' ===" -ForegroundColor Cyan
    Write-Host "Found: $($campaigns.Count) campaigns`n"
    
    # Group by contact
    $byContact = $campaigns | Group-Object Number
    
    foreach ($group in $byContact) {
        $contact = $ContactIndex[$group.Name]
        Write-Host "Contact: $($contact.whatsapp_contact) ($($group.Name))" -ForegroundColor Yellow
        foreach ($c in $group.Group) {
            Write-Host "  [$($c.Platform)] $($c.Beneficiary)"
        }
        Write-Host ""
    }
}

# List top contacts by campaign count
function Get-TopContacts {
    param([int]$Limit = 20)
    
    Write-Host "`n=== Top $Limit Contacts by Campaign Count ===" -ForegroundColor Cyan
    
    $VettingList | Sort-Object { [int]$_.campaign_count } -Descending | Select-Object -First $Limit | ForEach-Object {
        $name = if ($_.whatsapp_contact.Length -gt 30) { $_.whatsapp_contact.Substring(0, 30) + "..." } else { $_.whatsapp_contact }
        Write-Host ("  {0,-35} {1,3} campaigns  [{2}]" -f $name, $_.campaign_count, $_.platforms)
    }
}

# Stats summary
function Get-Stats {
    Write-Host "`n=== Database Statistics ===" -ForegroundColor Cyan
    
    $chuffedWithNumber = ($ChuffedCoupling | Where-Object { $_.number -and $_.number -notmatch "x.com" }).Count
    $whydonateWithNumber = ($WhydonateCoupling | Where-Object { $_.number }).Count
    
    Write-Host "`nCampaigns:"
    Write-Host "  Chuffed:   $($ChuffedCoupling.Count) total, $chuffedWithNumber with WhatsApp"
    Write-Host "  Whydonate: $($WhydonateCoupling.Count) total, $whydonateWithNumber with WhatsApp"
    Write-Host "  Total:     $($ChuffedCoupling.Count + $WhydonateCoupling.Count)"
    
    Write-Host "`nContacts:"
    Write-Host "  Unique:    $($VettingList.Count)"
    Write-Host "  Vetted:    $(($VettingList | Where-Object { $_.vetted }).Count)"
    
    $multiPlatform = ($VettingList | Where-Object { $_.platforms -eq "chuffed+whydonate" }).Count
    Write-Host "  Multi-platform: $multiPlatform"
    
    $avgCampaigns = ($VettingList | Measure-Object -Property campaign_count -Average).Average
    Write-Host "  Avg campaigns/contact: $([math]::Round($avgCampaigns, 1))"
}

# List unvetted contacts
function Get-Unvetted {
    Write-Host "`n=== Unvetted Contacts ===" -ForegroundColor Cyan
    
    $unvetted = $VettingList | Where-Object { -not $_.vetted -or $_.vetted -eq "" }
    Write-Host "Total unvetted: $($unvetted.Count)`n" -ForegroundColor Yellow
    
    $unvetted | Sort-Object { [int]$_.campaign_count } -Descending | ForEach-Object {
        $name = if ($_.whatsapp_contact.Length -gt 35) { $_.whatsapp_contact.Substring(0, 35) + "..." } else { $_.whatsapp_contact }
        Write-Host ("  {0,-40} {1,2} campaigns  {2}" -f $name, $_.campaign_count, $_.number)
    }
}

# List vetted contacts
function Get-Vetted {
    Write-Host "`n=== Vetted Contacts ===" -ForegroundColor Cyan
    
    $vetted = $VettingList | Where-Object { $_.vetted -and $_.vetted -ne "" }
    Write-Host "Total vetted: $($vetted.Count)`n" -ForegroundColor Green
    
    if ($vetted.Count -eq 0) {
        Write-Host "  No contacts vetted yet. Mark contacts in vetting_checklist.csv" -ForegroundColor Yellow
        return
    }
    
    $vetted | Sort-Object { [int]$_.campaign_count } -Descending | ForEach-Object {
        $name = if ($_.whatsapp_contact.Length -gt 35) { $_.whatsapp_contact.Substring(0, 35) + "..." } else { $_.whatsapp_contact }
        Write-Host ("  {0,-40} {1,2} campaigns  {2}" -f $name, $_.campaign_count, $_.number)
    }
}

# Find duplicate beneficiaries (same name, different numbers)
function Get-Duplicates {
    Write-Host "`n=== Potential Duplicates (same beneficiary, different contacts) ===" -ForegroundColor Cyan
    
    $allCampaigns = @()
    $ChuffedCoupling | ForEach-Object { $allCampaigns += [PSCustomObject]@{ Beneficiary = $_.beneficiary; Number = $_.number; Title = $_.title } }
    $WhydonateCoupling | ForEach-Object { $allCampaigns += [PSCustomObject]@{ Beneficiary = $_.beneficiary; Number = $_.number; Title = $_.whydonate_title } }
    
    $byName = $allCampaigns | Where-Object { $_.Beneficiary -and $_.Number } | Group-Object Beneficiary
    
    $duplicates = $byName | Where-Object { 
        ($_.Group | Select-Object -Unique Number).Count -gt 1 
    } | Sort-Object { $_.Group.Count } -Descending
    
    Write-Host "Found $($duplicates.Count) beneficiaries with multiple contacts:`n" -ForegroundColor Yellow
    
    foreach ($dup in $duplicates | Select-Object -First 20) {
        Write-Host "  $($dup.Name):" -ForegroundColor Cyan
        $dup.Group | Group-Object Number | ForEach-Object {
            $contact = $ContactIndex[$_.Name]
            $contactName = if ($contact) { $contact.whatsapp_contact } else { "Unknown" }
            Write-Host "    - $contactName ($($_.Name)): $($_.Count) campaigns"
        }
    }
}

# Search by raised amount
function Search-ByAmount {
    param([string]$Condition)
    
    Write-Host "`n=== Campaigns by Amount ===" -ForegroundColor Cyan
    
    if (-not $UnifiedCampaigns) {
        Write-Host "Unified campaigns not loaded" -ForegroundColor Red
        return
    }
    
    $results = @()
    
    # Parse condition (e.g., ">100", "<50", "=0")
    $op = $Condition[0]
    $value = [double]($Condition.Substring(1))
    
    foreach ($c in $UnifiedCampaigns) {
        $amount = [double]$c.raised_eur
        $match = switch ($op) {
            ">" { $amount -gt $value }
            "<" { $amount -lt $value }
            "=" { $amount -eq $value }
            default { $false }
        }
        
        if ($match) {
            $results += [PSCustomObject]@{
                Amount      = $amount
                Beneficiary = $c.privacy.first_name
                Title       = $c.title.Substring(0, [Math]::Min(50, $c.title.Length))
                Platform    = $c.platform
            }
        }
    }
    
    Write-Host "Found $($results.Count) campaigns where amount $Condition EUR`n" -ForegroundColor Yellow
    $results | Sort-Object Amount -Descending | Format-Table -AutoSize
}

# Export results to CSV
function Export-Results {
    param([string]$Type, [string]$Query)
    
    $outPath = Join-Path $DataPath "query_export_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
    
    $data = switch ($Type) {
        "contacts" { $VettingList }
        "unvetted" { $VettingList | Where-Object { -not $_.vetted } }
        "search" { Search-Campaign -Name $Query }
        default { $VettingList }
    }
    
    $data | Export-Csv $outPath -NoTypeInformation -Encoding UTF8
    Write-Host "Exported $($data.Count) rows to: $outPath" -ForegroundColor Green
}

# Find orphan campaigns (no contact info, but may have raised money = debt)
function Get-Orphans {
    Write-Host "`n=== Orphan Campaigns (no contact, potential debt) ===" -ForegroundColor Cyan
    Write-Host "These campaigns have no valid WhatsApp connection but may have raised money.`n" -ForegroundColor Yellow
    
    $orphans = @()
    
    # Process all unified campaigns
    foreach ($c in $UnifiedCampaigns) {
        $isChuffed = $c.platform -eq "chuffed"
        $pureId = if ($isChuffed) { $c.id.Replace("chuffed_", "") } else { "" }
        $title = $c.title
        $ben = $c.privacy.first_name
        
        $mapping = if ($isChuffed) { 
            $ChuffedCoupling | Where-Object { $_.chuffed_id -eq $pureId } 
        }
        else { 
            $WhydonateCoupling | Where-Object { $_.whydonate_title -eq $title } 
        }
        
        $isOrphan = $false
        $reason = ""
        $category = "" # true_orphan, gap, invalid
        $refNumber = ""

        if (-not $mapping) {
            # Check other platform
            $otherMapping = if ($isChuffed) {
                $WhydonateCoupling | Where-Object { $_.beneficiary -eq $ben -and $_.number -ne "" } | Select-Object -First 1
            }
            else {
                $ChuffedCoupling | Where-Object { $_.beneficiary -eq $ben -and $_.number -ne "" } | Select-Object -First 1
            }

            if ($otherMapping) {
                $category = "gap"
                $reason = "Known beneficiary (linked via $($otherMapping.number) on $(if ($isChuffed) { 'Whydonate' } else { 'Chuffed' }))"
                $refNumber = $otherMapping.number
            }
            else {
                $category = "true_orphan"
                $reason = "Beneficiary unknown in all mappings"
            }
            $isOrphan = $true
        }
        elseif (-not $mapping.number -or $mapping.number -eq "" -or $mapping.number -match "x.com" -or $mapping.number -match "@") {
            $category = "invalid"
            $reason = "Invalid/Missing number in current mapping"
            $isOrphan = $true
        }

        if ($isOrphan) {
            $orphans += [PSCustomObject]@{
                Platform    = $c.platform
                ID          = $pureId
                Beneficiary = $ben
                Title       = $title
                Contact     = if ($mapping) { $mapping.whatsapp_contact } else { "UNKNOWN" }
                Number      = if ($mapping) { $mapping.number } else { $refNumber }
                Raised      = $c.raised_eur
                HasDebt     = ($c.raised_eur -gt 0)
                Reason      = $reason
                Category    = $category
            }
        }
    }

    if ($orphans.Count -eq 0) {
        Write-Output "  No orphan campaigns found. All campaigns have valid contacts."
        return
    }
    
    $trueOrphans = $orphans | Where-Object { $_.Category -eq "true_orphan" }
    $gaps = $orphans | Where-Object { $_.Category -eq "gap" }
    $invalid = $orphans | Where-Object { $_.Category -eq "invalid" }
    
    $report = @()
    $report += "=== CAMPAIGN DATABASE RECONCILIATION REPORT ==="
    $report += "Total Orphan Entries: $($orphans.Count)"
    $report += "  - True Orphans (Unknown Persons): $($trueOrphans.Count)"
    $report += "  - Coupling Gaps (Known Persons, Missing Links): $($gaps.Count)"
    $report += "  - Invalid Data (Social Media Links instead of Numbers): $($invalid.Count)"
    $report += ""

    if (($trueOrphans | Where-Object { $_.HasDebt }).Count -gt 0) {
        $report += "!!! PRIORITY: TRUE ORPHANS WITH DEBT !!!"
        foreach ($o in $trueOrphans | Where-Object { $_.HasDebt } | Sort-Object Raised -Descending) {
            $report += "[$($o.Platform)] $($o.Beneficiary): €$($o.Raised)"
            $report += "  Title: $($o.Title)"
            $report += ""
        }
    }

    $report += "--- TRUE ORPHANS (Unknown Beneficiaries) ---"
    foreach ($o in $trueOrphans | Where-Object { -not $_.HasDebt }) {
        $report += "  [$($o.Platform)] $($o.Beneficiary): $($o.Title)"
    }

    $report += "`n--- COUPLING GAPS (Known Beneficiaries, link these campaigns!) ---"
    foreach ($o in $gaps | Sort-Object Number) {
        $report += "  [$($o.Platform)] $($o.Beneficiary) -> Mapped as: $($o.Number) ($($o.Reason))"
    }

    $report += "`n--- INVALID DATA (Fix these numbers) ---"
    foreach ($o in $invalid) {
        $report += "  [$($o.Platform)] $($o.Beneficiary): Number recorded as '$($o.Number)'"
    }

    Write-Output $report
}

# Interactive menu
function Show-Menu {
    Write-Host "`n=== Campaign Database Query Tool ===" -ForegroundColor Cyan
    Write-Host "Commands:"
    Write-Host "  search <name>     - Search campaigns by name"
    Write-Host "  contact <num>     - Get contact details by phone number"
    Write-Host "  beneficiary <n>   - List all campaigns for a beneficiary"
    Write-Host "  top [n]           - Show top N contacts (default 20)"
    Write-Host "  vetted            - List verified contacts"
    Write-Host "  unvetted          - List unverified contacts"
    Write-Host "  duplicates        - Find same beneficiary with different contacts"
    Write-Host "  amount <op>       - Search by amount (e.g., >100, =0, <50)"
    Write-Host "  orphans           - Find campaigns with no contact (check debt)"
    Write-Host "  export <type>     - Export to CSV (contacts, unvetted, search)"
    Write-Host "  stats             - Show database statistics"
    Write-Host "  help              - Show this menu"
    Write-Host "  exit              - Exit"
}

# Main
Load-Data

if ($Command) {
    # Non-interactive mode
    switch ($Command.ToLower()) {
        "search" { Search-Campaign -Name $Query | Format-Table -AutoSize }
        "contact" { Get-Contact -Number $Query }
        "beneficiary" { Get-Beneficiary -Name $Query }
        "top" { Get-TopContacts -Limit ([int]$Query) }
        "vetted" { Get-Vetted }
        "unvetted" { Get-Unvetted }
        "duplicates" { Get-Duplicates }
        "amount" { Search-ByAmount -Condition $Query }
        "orphans" { Get-Orphans }
        "export" { Export-Results -Type $Query -Query $Filter }
        "stats" { Get-Stats }
        default { Show-Menu }
    }
}
else {
    # Interactive mode
    Show-Menu
    
    while ($true) {
        Write-Host ""
        $userInput = Read-Host "query"
        
        if (-not $userInput) { continue }
        
        $parts = $userInput -split '\s+', 2
        $cmd = $parts[0].ToLower()
        $arg = if ($parts.Count -gt 1) { $parts[1] } else { "" }
        
        switch ($cmd) {
            "search" { Search-Campaign -Name $arg | Format-Table Platform, Beneficiary, Contact, Number -AutoSize }
            "contact" { Get-Contact -Number $arg }
            "beneficiary" { Get-Beneficiary -Name $arg }
            "top" { Get-TopContacts -Limit $(if ($arg) { [int]$arg } else { 20 }) }
            "vetted" { Get-Vetted }
            "unvetted" { Get-Unvetted }
            "duplicates" { Get-Duplicates }
            "amount" { Search-ByAmount -Condition $arg }
            "orphans" { Get-Orphans }
            "export" { Export-Results -Type $arg }
            "stats" { Get-Stats }
            "help" { Show-Menu }
            "exit" { return }
            "quit" { return }
            default { Write-Host "Unknown command: $cmd. Type 'help' for options." -ForegroundColor Yellow }
        }
    }
}
