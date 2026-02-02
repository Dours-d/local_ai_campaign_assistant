
param (
    [string]$ChuffedJson = "C:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\chuffed_campaigns.json",
    [string]$WhydonateJson = "C:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\whydonate_campaigns.json",
    [string]$MediaMappingCsv = "C:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\media_mapping.csv"
)

# Load Data
if (-not (Test-Path $ChuffedJson)) { Write-Error "Chuffed JSON missing"; exit 1 }
if (-not (Test-Path $WhydonateJson)) { Write-Error "Whydonate JSON missing"; exit 1 }
if (-not (Test-Path $MediaMappingCsv)) { Write-Error "Media Mapping CSV missing"; exit 1 }

$Chuffed = Get-Content $ChuffedJson | ConvertFrom-Json
$Whydonate = Get-Content $WhydonateJson | ConvertFrom-Json
$Mappings = Import-Csv $MediaMappingCsv

# Helper: Levenshtein Distance (C# Implementation)
$levSource = @"
public class Levenshtein {
    public static int Distance(string s, string t) {
        if (string.IsNullOrEmpty(s)) return string.IsNullOrEmpty(t) ? 0 : t.Length;
        if (string.IsNullOrEmpty(t)) return s.Length;
        int n = s.Length;
        int m = t.Length;
        int[,] d = new int[n + 1, m + 1];
        for (int i = 0; i <= n; i++) d[i, 0] = i;
        for (int j = 0; j <= m; j++) d[0, j] = j;
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                int cost = (System.Char.ToLower(t[j - 1]) == System.Char.ToLower(s[i - 1])) ? 0 : 1;
                d[i, j] = System.Math.Min(System.Math.Min(d[i - 1, j] + 1, d[i, j - 1] + 1), d[i - 1, j - 1] + cost);
            }
        }
        return d[n, m];
    }
}
"@
if (-not ([System.Management.Automation.PSTypeName]'Levenshtein').Type) { Add-Type -TypeDefinition $levSource }

Write-Host "Analyzing $($Chuffed.Count) Chuffed campaigns vs $($Whydonate.Count) Whydonate campaigns..."

$Report = @()

foreach ($c in $Chuffed) {
    if (-not $c.title) { continue }
    
    # 1. Find if already on Whydonate
    $MatchDist = 1000
    $BestWd = $null
    foreach ($w in $Whydonate) {
        $dist = [Levenshtein]::Distance($c.title, $w.project_title)
        if ($dist -lt $MatchDist) {
            $MatchDist = $dist
            $BestWd = $w
        }
    }

    $IsMigrated = $false
    if ($MatchDist -le 5) { $IsMigrated = $true } # Threshold for "Same Campaign"

    # 2. Find Originator from Media Mapping
    # Logic: Folders were mapped to Chuffed Slugs
    $Mapping = $Mappings | Where-Object { $_.MatchedSlug -eq $c.slug } | Select-Object -First 1

    $Report += [PSCustomObject]@{
        ChuffedTitle   = $c.title
        ChuffedStatus  = $c.status
        RaisedChuffed  = $c.raised
        IsOnWhydonate  = $IsMigrated
        WhydonateMatch = if ($BestWd) { $BestWd.project_title } else { "None" }
        MatchDistance  = $MatchDist
        Originator     = if ($Mapping) { $Mapping.Contact } else { "Unknown" }
        Beneficiary    = if ($Mapping) { $Mapping.Beneficiary } else { "Unknown" }
        Folder         = if ($Mapping) { $Mapping.Folder } else { "None" }
        ChuffedUrl     = $c.url
    }
}

$OutPath = "C:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\migration_report.csv"
$Report | Export-Csv -Path $OutPath -NoTypeInformation
Write-Host "Gap Analysis complete. Report saved to $OutPath"
