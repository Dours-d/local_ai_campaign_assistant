
# Anti-Gravity Backup Vault System
# Version: 1.0

param(
    [string]$SourceDir = ".",
    [string]$BackupBase = "backups",
    [string[]]$IncludePaths = @("data", "scripts", "src", "docs", "README.md", "chuffed_campaigns.json", "primary_campaign_dataset.csv", "whydonate_campaigns.json"),
    [string[]]$ExcludePatterns = @("*.pyc", "__pycache__", ".venv", ".git", ".gemini", "backups", "node_modules")
)

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$InternalDir = Join-Path $BackupBase "internal"
$VaultDir = Join-Path $BackupBase "vault/latest"
$ZipPath = Join-Path $InternalDir "backup_$Timestamp.zip"

Write-Host "=== Anti-Gravity Backup Vault ===" -ForegroundColor Cyan
Write-Host "Timestamp: $Timestamp" -ForegroundColor Gray

# 1. Prepare Directories
foreach ($dir in @($InternalDir, $VaultDir)) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

# 2. Backup B: Secure Vault (Raw Sync)
Write-Host "Phase 1: Mirroring to Secure Vault ($VaultDir)..." -ForegroundColor Yellow
# Clear latest vault
Remove-Item -Path "$VaultDir/*" -Recurse -Force -ErrorAction SilentlyContinue

foreach ($path in $IncludePaths) {
    if (Test-Path $path) {
        $dest = Join-Path $VaultDir (Split-Path $path -Leaf)
        Copy-Item -Path $path -Destination $dest -Recurse -Force
    }
}
Write-Host "  ✅ Vault mirror complete." -ForegroundColor Green

# 3. Backup A: Internal Archive (Timestamped Zip)
Write-Host "Phase 2: Creating Internal Archive ($ZipPath)..." -ForegroundColor Yellow
$ArchiveTemp = Join-Path $env:TEMP "ag_backup_$Timestamp"
if (Test-Path $ArchiveTemp) { Remove-Item $ArchiveTemp -Recurse -Force }
New-Item -ItemType Directory -Path $ArchiveTemp | Out-Null

# Copy files to temp for zipping (respecting exclusions)
foreach ($path in $IncludePaths) {
    if (Test-Path $path) {
        $dest = Join-Path $ArchiveTemp (Split-Path $path -Leaf)
        Copy-Item -Path $path -Destination $dest -Recurse -Force
    }
}

# Remove excluded patterns from temp
foreach ($pattern in $ExcludePatterns) {
    Get-ChildItem -Path $ArchiveTemp -Filter $pattern -Recurse | Remove-Item -Recurse -Force
}

Compress-Archive -Path "$ArchiveTemp/*" -DestinationPath $ZipPath -Force
Remove-Item $ArchiveTemp -Recurse -Force

Write-Host "  ✅ Internal archive complete: $(Split-Path $ZipPath -Leaf)" -ForegroundColor Green

# 4. Integrity Check (MD5)
Write-Host "Phase 3: Integrity Validation..." -ForegroundColor Yellow
$Hash = Get-FileHash -Path $ZipPath -Algorithm MD5
$HashPath = $ZipPath + ".md5"
$Hash.Hash | Out-File -FilePath $HashPath -Encoding utf8
Write-Host "  ✅ MD5: $($Hash.Hash)" -ForegroundColor Green

Write-Host "`n=== Backup Strategy Executed Successfully ===" -ForegroundColor Cyan
