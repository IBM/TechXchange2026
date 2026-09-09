# =============================================================================
# Configure-CiscoVPN.ps1
# Lab 3967 - zSecure Detection | TechXChange 2026
#
# PURPOSE : Adds the lab VPN server to the Cisco AnyConnect profile.
#           Cisco AnyConnect Secure Client must already be installed.
#
# RUN AS  : Administrator
# USAGE   : PowerShell -ExecutionPolicy Bypass -File .\Configure-CiscoVPN.ps1
# =============================================================================

# --- Configuration -----------------------------------------------------------
$VpnHostName    = "Lab 3967 VPN"
$VpnHostAddress = "asa003b.centers.ihost.com"
$ProfileDir     = "$env:ProgramData\Cisco\Cisco Secure Client\VPN\Profile"
$ProfileFile    = "$ProfileDir\Lab3967.xml"
$ServiceName    = "csc_vpnagent"
# -----------------------------------------------------------------------------

# --- Enforce Administrator -----------------------------------------------
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host ""
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    Write-Host "       Right-click PowerShell and select 'Run as Administrator'," -ForegroundColor Red
    Write-Host "       or use: Start-Process PowerShell -Verb RunAs" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Lab 3967 - Cisco AnyConnect VPN Setup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Verify AnyConnect service exists
Write-Host "[1/4] Checking AnyConnect service..." -ForegroundColor Yellow
if (-not (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Cisco AnyConnect service '$ServiceName' not found." -ForegroundColor Red
    Write-Host "       Make sure Cisco AnyConnect Secure Client is installed." -ForegroundColor Red
    exit 1
}
Write-Host "      Service found: $ServiceName" -ForegroundColor Green

# Step 2 - Create profile directory if missing
Write-Host "[2/4] Checking profile directory..." -ForegroundColor Yellow
if (-not (Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
    Write-Host "      Created: $ProfileDir" -ForegroundColor Green
} else {
    Write-Host "      Exists:  $ProfileDir" -ForegroundColor Green
}

# Step 3 - Write the profile XML
Write-Host "[3/4] Writing VPN profile..." -ForegroundColor Yellow
@"
<?xml version="1.0" encoding="UTF-8"?>
<AnyConnectProfile xmlns="http://schemas.xmlsoap.org/encoding/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                   xsi:schemaLocation="http://schemas.xmlsoap.org/encoding/ AnyConnectProfile.xsd">
  <ServerList>
    <HostEntry>
      <HostName>$VpnHostName</HostName>
      <HostAddress>$VpnHostAddress</HostAddress>
    </HostEntry>
  </ServerList>
</AnyConnectProfile>
"@ | Set-Content -Path $ProfileFile -Encoding UTF8
Write-Host "      Written:  $ProfileFile" -ForegroundColor Green

# Step 4 - Kill ALL Cisco processes, force stop/start service to load new profile
Write-Host "[4/4] Restarting AnyConnect service..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.Name -like "*csc*" -or $_.Name -like "*vpn*" -or $_.Name -like "*cisco*" } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
try {
    Stop-Service -Name $ServiceName -Force -ErrorAction Stop
} catch {
    Write-Host "ERROR: Could not stop service '$ServiceName': $_" -ForegroundColor Red
    Write-Host "       Make sure the script is running as Administrator." -ForegroundColor Red
    exit 1
}
Start-Sleep -Seconds 5
try {
    Start-Service -Name $ServiceName -ErrorAction Stop
} catch {
    Write-Host "ERROR: Could not start service '$ServiceName': $_" -ForegroundColor Red
    exit 1
}
Write-Host "      Service restarted." -ForegroundColor Green

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " SUCCESS: VPN server configured." -ForegroundColor Green
Write-Host " Server : $VpnHostAddress" -ForegroundColor Green
Write-Host " Open Cisco AnyConnect - server appears in" -ForegroundColor Green
Write-Host " the dropdown. Enter userid + password." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
