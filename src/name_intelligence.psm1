# Arabic Name Intelligence Module
# Handles Islamic naming particles and normalizes beneficiary names

# Islamic naming particles and their meanings
$NameParticles = @{
    # Kunya (parental honorifics) - "Father of" / "Mother of"
    "abu"     = @{ type = "kunya"; gender = "male"; meaning = "father of" }
    "abou"    = @{ type = "kunya"; gender = "male"; meaning = "father of" }
    "abo"     = @{ type = "kunya"; gender = "male"; meaning = "father of" }
    "um"      = @{ type = "kunya"; gender = "female"; meaning = "mother of" }
    "umm"     = @{ type = "kunya"; gender = "female"; meaning = "mother of" }
    "om"      = @{ type = "kunya"; gender = "female"; meaning = "mother of" }
    "oum"     = @{ type = "kunya"; gender = "female"; meaning = "mother of" }
    
    # Nasab (lineage) - "Son of" / "Daughter of"
    "ibn"     = @{ type = "nasab"; gender = "male"; meaning = "son of" }
    "bin"     = @{ type = "nasab"; gender = "male"; meaning = "son of" }
    "ben"     = @{ type = "nasab"; gender = "male"; meaning = "son of" }
    "bint"    = @{ type = "nasab"; gender = "female"; meaning = "daughter of" }
    
    # Nisbah (origin/affiliation)
    "al"      = @{ type = "nisbah"; meaning = "the" }
    "el"      = @{ type = "nisbah"; meaning = "the" }
    
    # Common family/relationship words
    "sister"  = @{ type = "relation"; gender = "female"; meaning = "sister" }
    "brother" = @{ type = "relation"; gender = "male"; meaning = "brother" }
}

function Get-NormalizedName {
    param([string]$RawName, [string]$Title)
    
    $name = $RawName.Trim()
    $nameLower = $name.ToLower()
    
    # Check if name is a particle itself
    if ($NameParticles.ContainsKey($nameLower)) {
        $particle = $NameParticles[$nameLower]
        
        # Try to extract the actual name from the title
        # Pattern: "Help [particle] [Name]..." or "Save [particle] [Name]..."
        
        if ($particle.type -eq "kunya") {
            # For Abu/Umm patterns, the next word is their child's name
            # Try to find their actual name in the title
            $patterns = @(
                "(?:Help|Save|Support)\s+(?:$nameLower)\s+(\w+(?:\s+\w+)?)",
                "(?:$nameLower)\s+(\w+)"
            )
            
            foreach ($pattern in $patterns) {
                if ($Title -match $pattern) {
                    $childName = $matches[1]
                    # Return kunya with child's name
                    return @{
                        display    = "$name $childName"
                        type       = $particle.type
                        gender     = $particle.gender
                        child_name = $childName
                        original   = $RawName
                    }
                }
            }
        }
        elseif ($particle.type -eq "relation") {
            # For "sister" or "brother", extract the actual name
            $patterns = @(
                "(?:Help|Save|Support)\s+(?:our\s+)?(?:elder\s+)?(?:$nameLower)\s+(\w+)",
                "(?:$nameLower)\s+(\w+)"
            )
            
            foreach ($pattern in $patterns) {
                if ($Title -match $pattern) {
                    $actualName = $matches[1]
                    if ($actualName -notmatch "^(and|with|from|to|in|for|her|his|the)$") {
                        return @{
                            display  = $actualName
                            type     = "name"
                            gender   = $particle.gender
                            original = $RawName
                            note     = "Extracted from '$RawName'"
                        }
                    }
                }
            }
        }
    }
    
    # Check for embedded particles
    foreach ($particleKey in $NameParticles.Keys) {
        if ($nameLower -match "^$particleKey\s+") {
            $particle = $NameParticles[$particleKey]
            $remainder = $name -replace "(?i)^$particleKey\s+", ""
            
            return @{
                display   = $name
                type      = $particle.type
                gender    = $particle.gender
                base_name = $remainder
                original  = $RawName
            }
        }
    }
    
    # No particle detected, return as-is
    return @{
        display  = $name
        type     = "name"
        original = $RawName
    }
}

# Process a vetting file and normalize names
function Update-VettingFileNames {
    param([string]$FilePath)
    
    $data = Import-Csv $FilePath
    $updated = 0
    
    foreach ($row in $data) {
        $titleCol = if ($row.PSObject.Properties.Name -contains "whydonate_title") { "whydonate_title" } else { "title" }
        $title = $row.$titleCol
        $beneficiary = $row.beneficiary
        
        if (-not $beneficiary) { continue }
        
        $normalized = Get-NormalizedName -RawName $beneficiary -Title $title
        
        if ($normalized.display -ne $beneficiary) {
            Write-Host "  $beneficiary -> $($normalized.display)" -ForegroundColor Cyan
            $row.beneficiary = $normalized.display
            $updated++
        }
    }
    
    return @{ data = $data; updated = $updated }
}

# Export functions
Export-ModuleMember -Function Get-NormalizedName, Update-VettingFileNames -Variable NameParticles
