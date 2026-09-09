# =============================================================================
# Configure-PCOMMSession.ps1
# Lab 3967 - zSecure Detection | TechXChange 2026
#
# PURPOSE : Creates an IBM PCOMM (Personal Communications) session file
#           for the lab mainframe connection.
#
#           Session: Lab-3967
#           Type   : zSeries (3270)
#           Link   : Telnet3270 over LAN
#           Host   : ex167n01.pbm.ihost.com:9023
#           TLS    : Enabled
#
# RUN AS  : Current user (no elevation required)
# USAGE   : PowerShell -ExecutionPolicy Bypass -File .\Configure-PCOMMSession.ps1
# =============================================================================

# --- Configuration -----------------------------------------------------------
$SessionName  = "Lab-3967"
$HostName     = "ex167n01.pbm.ihost.com"
$HostPort     = "9023"
# -----------------------------------------------------------------------------

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Lab 3967 - PCOMM Session Setup"             -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Locate PCOMM installation
Write-Host "[1/4] Locating PCOMM installation..." -ForegroundColor Yellow
$pcommPaths = @(
    "$env:ProgramFiles\IBM\Personal Communications",
    "${env:ProgramFiles(x86)}\IBM\Personal Communications"
)
$pcommDir = $pcommPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $pcommDir) {
    Write-Host "ERROR: IBM Personal Communications not found." -ForegroundColor Red
    Write-Host "       Please install PCOMM first." -ForegroundColor Red
    exit 1
}
Write-Host "      Found: $pcommDir" -ForegroundColor Green

# Step 2 - Resolve session file output directory
# PCOMM looks for session files in AppData\Roaming\IBM Personal Communications
# Resolve the correct user profile even when run as Administrator:
# use Invoke-CimMethod to call GetOwner() on the explorer.exe process
Write-Host "[2/4] Resolving session directory..." -ForegroundColor Yellow
$explorerProc = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" |
    Select-Object -First 1
$ownerResult = $explorerProc | Invoke-CimMethod -MethodName "GetOwner"
if ($ownerResult -and $ownerResult.User) {
    $userProfile = "C:\Users\$($ownerResult.User)"
} else {
    # Fallback: use whoever is running the script
    $userProfile = $env:USERPROFILE
}
$sessionDir = "$userProfile\AppData\Roaming\IBM\Personal Communications"
if (-not (Test-Path $sessionDir)) {
    New-Item -ItemType Directory -Force -Path $sessionDir | Out-Null
    Write-Host "      Created: $sessionDir" -ForegroundColor Green
} else {
    Write-Host "      Exists:  $sessionDir" -ForegroundColor Green
}
$sessionFile = "$sessionDir\$SessionName.WS"

# Step 3 - Write the .WS session file
Write-Host "[3/4] Writing session file..." -ForegroundColor Yellow

# .WS file format derived from existing working sessions on this machine
$wsContent = @"
[Profile]
UID=$(([guid]::NewGuid()).ToString())
Version=9
ID=WS
[Telnet3270]
HostName=$HostName
HostPortNumber=$HostPort
Security=Y
SecurityPackage=MS
AutoReconnect=Y
CertSelection=AUTOSELECT
SNIServerName=
[KeepAlive]
EnableTelnetKeepAlive=Y
[Communication]
Link=telnet3270
[3270]
QueryReplyMode=Auto
HostCodePage=037-U
[Keyboard]
CuaKeyboard=1
Language=United-States
DefaultKeyboard=$userProfile\AppData\Roaming\IBM\Personal Communications\TN3270.KMP
IBMDefaultKeyboard=N
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($sessionFile, $wsContent, $utf8NoBom)
Write-Host "      Written: $sessionFile" -ForegroundColor Green

# Step 4 - Verify file exists and contains key values
Write-Host "[4/4] Verifying session file..." -ForegroundColor Yellow
if (-not (Test-Path $sessionFile)) {
    Write-Host "ERROR: Session file was not created." -ForegroundColor Red
    exit 1
}
$content = Get-Content $sessionFile -Raw
$checks = @("Profile", $HostName, $HostPort, "Security=Y")
foreach ($check in $checks) {
    if ($content -notmatch [regex]::Escape($check)) {
        Write-Host "ERROR: Session file missing expected value: $check" -ForegroundColor Red
        exit 1
    }
}
Write-Host "      Verification passed." -ForegroundColor Green

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " SUCCESS: PCOMM session created."             -ForegroundColor Green
Write-Host ""
Write-Host " Session : $SessionName"                      -ForegroundColor Green
Write-Host " Host    : ${HostName}:${HostPort}"           -ForegroundColor Green
Write-Host " Security: TLS Enabled"                       -ForegroundColor Green
Write-Host " File    : $sessionFile"                      -ForegroundColor Green
Write-Host ""
Write-Host " Open PCOMM and load the session file, or"   -ForegroundColor Green
Write-Host " double-click $SessionName.WS to launch."     -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
