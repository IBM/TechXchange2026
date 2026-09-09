# =============================================================================
# Configure-FirefoxBookmarks.ps1
# Lab 3967 - zSecure Detection | TechXChange 2026
#
# PURPOSE : Adds lab bookmarks to Firefox toolbar using Mozilla Enterprise
#           Policy (policies.json). No profile hacking required.
#           Firefox must already be installed.
#
# RUN AS  : Administrator
# USAGE   : PowerShell -ExecutionPolicy Bypass -File .\Configure-FirefoxBookmarks.ps1
# =============================================================================

# --- Enforce Administrator ---------------------------------------------------
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host ""
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    exit 1
}

# --- Bookmarks Configuration -------------------------------------------------
# To add/remove bookmarks, edit this list only. Format:
#   @{ Title = "Display Name"; URL = "https://..." }
$Bookmarks = @(
    @{ Title = "TechXChange 2026";  URL = "https://ibm.biz/txc2026" },
    @{ Title = "zSecure Dashboard"; URL = "https://ex167n01.pbm.ihost.com:3841" },
    @{ Title = "z/OSMF";            URL = "https://ex167n01.pbm.ihost.com:443/zosmf" }
)
# -----------------------------------------------------------------------------

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Lab 3967 - Firefox Bookmarks Setup"          -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Find Firefox installation
Write-Host "[1/5] Locating Firefox installation..." -ForegroundColor Yellow
$firefoxPaths = @(
    "C:\Program Files\Mozilla Firefox",
    "C:\Program Files (x86)\Mozilla Firefox"
)
$firefoxDir = $firefoxPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $firefoxDir) {
    Write-Host "ERROR: Firefox not found. Please install Firefox first." -ForegroundColor Red
    exit 1
}
Write-Host "      Found: $firefoxDir" -ForegroundColor Green

# Step 2 - Close Firefox if running so policy is picked up on next open
Write-Host "[2/5] Closing Firefox if running..." -ForegroundColor Yellow
$ffProcess = Get-Process -Name firefox -ErrorAction SilentlyContinue
if ($ffProcess) {
    Stop-Process -Name firefox -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "      Firefox closed." -ForegroundColor Green
} else {
    Write-Host "      Firefox was not running." -ForegroundColor Green
}

# Step 3 - Create distribution directory
Write-Host "[3/5] Checking policy directory..." -ForegroundColor Yellow
$policyDir = "$firefoxDir\distribution"
if (-not (Test-Path $policyDir)) {
    New-Item -ItemType Directory -Force -Path $policyDir | Out-Null
    Write-Host "      Created: $policyDir" -ForegroundColor Green
} else {
    Write-Host "      Exists:  $policyDir" -ForegroundColor Green
}

# Step 4 - Build and write policies.json WITHOUT BOM (required by Firefox)
Write-Host "[4/5] Writing bookmarks policy..." -ForegroundColor Yellow

$bookmarkList = $Bookmarks | ForEach-Object {
    [PSCustomObject]@{ Title = $_.Title; URL = $_.URL; Placement = "toolbar"; Folder = "Lab Links" }
}
$policyObject = [PSCustomObject]@{
    policies = [PSCustomObject]@{
        Bookmarks               = $bookmarkList
        DisplayBookmarksToolbar = "always"
    }
}
$policiesJson = $policyObject | ConvertTo-Json -Depth 5

$policyFile = "$policyDir\policies.json"
# UTF8Encoding($false) writes UTF-8 WITHOUT BOM - Firefox rejects files with BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($policyFile, $policiesJson, $utf8NoBom)
Write-Host "      Written: $policyFile" -ForegroundColor Green

# Step 5 - Verify file exists, contains bookmarks, and has no BOM
Write-Host "[5/5] Verifying policy file..." -ForegroundColor Yellow
if (-not (Test-Path $policyFile)) {
    Write-Host "ERROR: Policy file was not created." -ForegroundColor Red
    exit 1
}
$content = Get-Content $policyFile -Raw
if ($content -notmatch "Bookmarks") {
    Write-Host "ERROR: Policy file content looks incorrect." -ForegroundColor Red
    exit 1
}
$bytes = [System.IO.File]::ReadAllBytes($policyFile)
if ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
    Write-Host "ERROR: BOM detected in policy file - Firefox will not read it." -ForegroundColor Red
    exit 1
}
Write-Host "      Verification passed (no BOM, content valid)." -ForegroundColor Green

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " SUCCESS: Firefox bookmarks configured."      -ForegroundColor Green
Write-Host ""
foreach ($bm in $Bookmarks) {
    Write-Host "   [+] $($bm.Title)" -ForegroundColor Green
    Write-Host "       $($bm.URL)"   -ForegroundColor Gray
}
Write-Host ""
Write-Host " Open Firefox - bookmarks are on the toolbar." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
