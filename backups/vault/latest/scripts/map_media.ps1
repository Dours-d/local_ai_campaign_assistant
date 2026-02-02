
param (
    [string]$MediaDir = "C:\Users\gaelf\Pictures\GAZA",
    [string]$CampaignsJson = "C:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\chuffed_campaigns.json"
)

# Load Campaigns
if (-not (Test-Path $CampaignsJson)) {
    Write-Error "Campaigns JSON not found: $CampaignsJson"
    exit 1
}
$Campaigns = Get-Content $CampaignsJson | ConvertFrom-Json

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
if (-not ([System.Management.Automation.PSTypeName]'Levenshtein').Type) {
    Add-Type -TypeDefinition $levSource
}

# Normalize string and return tokens
function Get-Tokens {
    param ([string]$str)
    $clean = $str -replace "[^a-zA-Z0-9\s]", " " `
        -replace "\s+", " "
    $tokens = $clean.Trim().ToLower().Split(" ") | Where-Object { 
        $_.Length -gt 2 -and $_ -notin @("help", "support", "gaza", "palestine", "family", "rebuild", "lives", "the", "and", "for", "lives") 
    }
    return $tokens
}

$Mapping = @()

# Process Media Folders
$Folders = Get-ChildItem -Path $MediaDir -Directory
Write-Host "Processing $($Folders.Count) folders..."

foreach ($Folder in $Folders) {
    $FolderName = $Folder.Name
    $Beneficiary = $FolderName
    $Contact = ""
    
    if ($FolderName -match "(.+?)\s*\((.+?)\)") {
        $Beneficiary = $matches[1].Trim()
        $Contact = $matches[2].Trim()
    }

    $FolderTokens = Get-Tokens $Beneficiary
    
    $BestMatch = $null
    $MaxScore = -1
    $MinDistScore = 1000

    foreach ($Camp in $Campaigns) {
        if (-not $Camp.title -or $Camp.slug -eq "ppoobb" -or $Camp.title.ToLower().Trim() -eq "gaza") { continue }
        
        $CampSlugTokens = Get-Tokens ($Camp.slug -replace "\d+-", "") # Remove ID prefix
        
        $MatchCount = 0
        foreach ($t in $FolderTokens) {
            if ($CampSlugTokens -contains $t) {
                $MatchCount++
            }
        }

        # Scoring: (Matches / Total Folder Tokens) * 100
        $Score = 0
        if ($FolderTokens.Count -gt 0) {
            $Score = ($MatchCount / $FolderTokens.Count) * 100
        }

        # Tie-breaker: Levenshtein on the name parts
        $Dist = [Levenshtein]::Distance($Beneficiary.ToLower(), $Camp.title.ToLower())
        
        if ($Score -gt $MaxScore -or ($Score -eq $MaxScore -and $Dist -lt $MinDistScore)) {
            $MaxScore = $Score
            $MinDistScore = $Dist
            $BestMatch = $Camp
        }
    }
    
    $MatchStatus = "Low"
    if ($MaxScore -ge 90) { $MatchStatus = "High" }
    elseif ($MaxScore -ge 50) { $MatchStatus = "Medium" }

    $Mapping += [PSCustomObject]@{
        Folder       = $FolderName
        Beneficiary  = $Beneficiary
        Contact      = $Contact
        MatchedTitle = if ($BestMatch) { $BestMatch.title } else { "None" }
        MatchedSlug  = if ($BestMatch) { $BestMatch.slug } else { "None" }
        MatchedUrl   = if ($BestMatch) { $BestMatch.url } else { "None" }
        TokenScore   = $MaxScore
        DistScore    = $MinDistScore
        Confidence   = $MatchStatus
    }
}

$OutPath = Join-Path $PSScriptRoot "..\data\media_mapping.csv"
$Mapping | Export-Csv -Path $OutPath -NoTypeInformation
Write-Host "Mapping completed. Saved to $OutPath"
