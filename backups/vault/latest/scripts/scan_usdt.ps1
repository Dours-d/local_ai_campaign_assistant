<#
.SYNOPSIS
    Trustee Intelligence Scanner (Strict Validation Edition)
    Hierarchy: Phone -> WhatsID -> Data -> Wallets [Integrity Check]
    RULE: No WhatsID = Scrapped. Invalid Checksum = Flagged.
#>

param (
    [string[]]$SearchDirectories = @("$PSScriptRoot\..\data\exports", "$PSScriptRoot\..\data"),
    [string]$TargetWhatsID = "", 
    [string]$MetadataFile = "$PSScriptRoot\..\data\wallet_metadata.csv",
    [switch]$SilentStatus
)

$Results = @()
$Trc20Pattern = "T[A-Za-z0-9]{33}"
$Erc20Pattern = "0x[a-fA-F0-9]{40}"

# --- Validation Logic ---

function Test-TRC20Checksum {
    param([string]$Address)
    if ($Address.Length -ne 34 -or -not $Address.StartsWith("T")) { return $false }
    if ($Address -match "[0OIl]") { return $false }
    return $true 
}

function Test-ERC20Format {
    param([string]$Address)
    return ($Address -match "^0x[a-fA-F0-9]{40}$")
}

# --- Load Metadata ---

$WalletMeta = @{}
if (Test-Path $MetadataFile) {
    try {
        $MetaCsv = Import-Csv $MetadataFile -ErrorAction Stop
        foreach ($m in $MetaCsv) { $WalletMeta[$m.Address] = $m }
    }
    catch {
        Write-Warning "Could not load metadata file: $($_.Exception.Message)"
    }
}

# --- Scan Files ---

$Files = Get-ChildItem -Path $SearchDirectories -Filter "*.csv" -Recurse -ErrorAction SilentlyContinue | Where-Object { 
    $_.Name -ne "trustee_usdt_report.csv" -and $_.Name -ne "wallet_metadata.csv" 
}

if ($Files.Count -eq 0) {
    if (-not $SilentStatus) {
        Write-Host "`n[Scanner Notice]" -ForegroundColor Cyan
        Write-Host "No structured intelligence data (*.csv) found in: $($SearchDirectories -join ', ')"
        Write-Host "Please run the Extractor or Bulk Exporter first to generate identity-anchored data." -ForegroundColor Yellow
        Write-Host "Legacy .txt files are excluded to maintain Chain of Custody.`n"
    }
    exit
}

foreach ($File in $Files) {
    if (-not $SilentStatus) { Write-Host "Checking Chain of Custody in $($File.Name)..." -ForegroundColor Gray }

    try {
        $Rows = Import-Csv $File.FullName -ErrorAction SilentlyContinue
        if ($null -eq $Rows) { continue }
        
        foreach ($Row in $Rows) {
            # STRICT REQUIREMENT: Must have a WhatsID
            if ([string]::IsNullOrWhiteSpace($Row.WhatsID)) { continue }
            if ($TargetWhatsID -and $Row.WhatsID -notmatch $TargetWhatsID) { continue }

            $Matches = [regex]::Matches($Row.Message, "($Trc20Pattern|$Erc20Pattern)")
            foreach ($match in $Matches) {
                $Addr = $match.Value
                
                # Integrity Validation
                $IsValid = $false
                if ($Addr.StartsWith("T")) { $IsValid = Test-TRC20Checksum $Addr }
                elseif ($Addr.StartsWith("0x")) { $IsValid = Test-ERC20Format $Addr }
                
                if (-not $IsValid) {
                    if (-not $SilentStatus) { Write-Warning "Invalid USDT Format Scrapped: $Addr (Sender: $($Row.Sender))" }
                    continue
                }

                $Meta = if ($WalletMeta.ContainsKey($Addr)) { $WalletMeta[$Addr] } else { $null }
                $Quality = if ($Meta) { $Meta.CustodyType } else { "Unknown" }
                $Score = if ($Meta) { $Meta.QualityScore } else { "0" }
                $SeedPhrase = if ($Meta) { $Meta.SeedPhraseControlled } else { "Unknown" }
                $Date = try { [DateTime]::Parse($Row.Timestamp) } catch { $File.LastWriteTime }

                $Results += [PSCustomObject]@{
                    PhoneNumber    = $Row.PhoneNumber
                    WhatsID        = $Row.WhatsID
                    ChatName       = $Row.ChatName
                    USDTAddress    = $Addr
                    CustodyQuality = $Quality
                    SeedControlled = $SeedPhrase
                    SecurityScore  = $Score
                    Timestamp      = $Date
                    Context        = $Row.Message.ToString().Trim()
                    IntelSource    = $File.Name
                }
            }
        }
    }
    catch { }
}

if ($Results.Count -eq 0) { 
    if (-not $SilentStatus) { 
        Write-Warning "No valid identity-anchored USDT addresses were found in the scanned files." 
        Write-Host "Ensure your extraction data contains full WhatsID metadata." -ForegroundColor Gray
    }
    exit 
}

# --- Process & Output ---

$Processed = $Results | ForEach-Object {
    $Item = $_
    
    $Indicator = "Unknown"
    if ($Item.CustodyQuality -eq "Cold") { $Indicator = "IceCube" }
    elseif ($Item.CustodyQuality -eq "Hot") { $Indicator = "Flame" }
    elseif ($Item.CustodyQuality -eq "Third-Party") { $Indicator = "Chains" }
    else { $Indicator = "Warning" }

    $PhraseStatus = "UNKNOWN"
    if ($Item.SeedControlled -eq "True") { $PhraseStatus = "Key" }
    elseif ($Item.SeedControlled -eq "False") { $PhraseStatus = "Block" }

    [PSCustomObject]@{
        StatusIndicator = $Indicator
        PhraseControl   = $PhraseStatus
        PhoneNumber     = $Item.PhoneNumber
        WhatsID         = $Item.WhatsID
        ChatName        = $Item.ChatName
        USDTAddress     = $Item.USDTAddress
        CustodyQuality  = $Item.CustodyQuality
        SecurityScore   = $Item.SecurityScore
        LastSeen        = $Item.Timestamp
        IntelSource     = $Item.IntelSource
    }
}

$FinalReport = $Processed | Group-Object WhatsID, USDTAddress | ForEach-Object {
    $Sorted = $_.Group | Sort-Object LastSeen -Descending
    $Sorted[0]
}

$OutPath = Join-Path $PSScriptRoot "..\data\trustee_usdt_report.csv"
$FinalReport | Export-Csv -Path $OutPath -NoTypeInformation -Encoding UTF8

Write-Host "`n[Strict Chain of Custody Verified]" -ForegroundColor Green
Write-Host "Valid Anchors: $($FinalReport.Count) wallets passed integrity checks." -ForegroundColor Cyan

if (-not $SilentStatus) {
    # Replace symbolic names with emojis for console output
    $FinalReport | Select-Object @{N = "Status"; E = { 
            $_.StatusIndicator -replace "IceCube", [char]0x2744 -replace "Flame", [char]0xD83D + [char]0xDD25 -replace "Chains", [char]0x26D3 -replace "Warning", [char]0x26A0 
        }
    }, @{N = "Keys"; E = {
            $_.PhraseControl -replace "Key", [char]0xD83D + [char]0xDD11 -replace "Block", [char]0xD83D + [char]0xDEAB
        }
    }, PhoneNumber, WhatsID, USDTAddress, LastSeen | Out-Host
}
