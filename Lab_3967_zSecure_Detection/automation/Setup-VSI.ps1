# =============================================================================
# Setup-VSI.ps1
# Lab 3967 - zSecure Detection | TechXChange 2026
#
# PURPOSE : Single self-contained post-provisioning script. Run once on each
#           VSI as Administrator to apply all lab configurations:
#
#             1. Install IBM Internal Root CA certificate
#             2. Configure Cisco Secure Client VPN server
#             3. Configure Firefox bookmarks toolbar
#             4. Create PCOMM Telnet3270 session
#
# RUN AS  : Administrator (TechZone cloud-init handler runs as SYSTEM/Administrator)
# USAGE   : PowerShell -ExecutionPolicy Bypass -File .\Setup-VSI.ps1
#           PowerShell -ExecutionPolicy Bypass -File .\Setup-VSI.ps1 .\post_deploy_variables.json
# =============================================================================

# --- TechZone framework: variables file is passed as first argument ----------
param([string]$VarsFile = ".\post_deploy_variables.json")

# --- Enforce Administrator ---------------------------------------------------
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host ""
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    exit 1
}

# =============================================================================
# CONFIGURATION - edit here only
# =============================================================================

# --- VPN ---------------------------------------------------------------------
$VpnHostName    = "Lab 3967 VPN"
$VpnHostAddress = "asa003b.centers.ihost.com"
$VpnProfileDir  = "$env:ProgramData\Cisco\Cisco Secure Client\VPN\Profile"
$VpnServiceName = "csc_vpnagent"

# --- Firefox Bookmarks -------------------------------------------------------
$FirefoxBookmarks = @(
    @{ Title = "TechXChange 2026";  URL = "https://ibm.biz/txc2026" },
    @{ Title = "zSecure Dashboard"; URL = "https://ex167n01.pbm.ihost.com:3841" },
    @{ Title = "z/OSMF";            URL = "https://ex167n01.pbm.ihost.com:443/zosmf" }
)
$FirefoxFolder = "Lab Links"

# --- PCOMM -------------------------------------------------------------------
$PCOMMSessionName = "Lab-3967"
$PCOMMHost        = "ex167n01.pbm.ihost.com"
$PCOMMPort        = "9023"

# --- IBM Root CA Certificate -------------------------------------------------
$CertBase64 = @"
MIID5TCCAs2gAwIBAgIBFDANBgkqhkiG9w0BAQsFADBiMQswCQYDVQQGEwJVUzE0
MDIGA1UEChMrSW50ZXJuYXRpb25hbCBCdXNpbmVzcyBNYWNoaW5lcyBDb3Jwb3Jh
dGlvbjEdMBsGA1UEAxMUSUJNIEludGVybmFsIFJvb3QgQ0EwHhcNMTYwMjI0MDUw
MDAwWhcNMzUwMTAzMDQ1OTU5WjBiMQswCQYDVQQGEwJVUzE0MDIGA1UEChMrSW50
ZXJuYXRpb25hbCBCdXNpbmVzcyBNYWNoaW5lcyBDb3Jwb3JhdGlvbjEdMBsGA1UE
AxMUSUJNIEludGVybmFsIFJvb3QgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
ggEKAoIBAQDUKGuk9Tmri43R3SauS7gY9rQ9DXvRwklnbW+3Ts8/Meb4MPPxezdE
cqVJtHVc3kinDpzVMeKJXlB8CABBpxMBSLApmIQywEKoVd0H0w62Yc3rYuhv03iY
y6OozBV0BL6tzZE0UbvtLGuAQXMZ7ehzxqIta85JjfFN86AO2u7xrNF0FYyGH+E0
Rn6yNhb25VrqxE0OYbSMIGoWdvS11K4SgVDqrJ9OqIk8NHrIJ8Ed24P/YPMeAp3j
U409Gev1zGcuLdRr09WckQ145FZVDbPq42gcl7qYICPhZ4/eDUUjFgxpipfMGkMb
1X+Y3kFDgb4BO8Xrdda2VQo1iDZs8A8bAgMBAAGjgaUwgaIwPwYJYIZIAYb4QgEN
BDIWMEdlbmVyYXRlZCBieSB0aGUgU2VjdXJpdHkgU2VydmVyIGZvciB6L09TIChS
QUNGKTAOBgNVHQ8BAf8EBAMCAQYwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQU+d4Y5Z4w
E2lRp/15hUiMfA5v2OMwHwYDVR0jBBgwFoAU+d4Y5Z4wE2lRp/15hUiMfA5v2OMw
DQYJKoZIhvcNAQELBQADggEBAH87Ms8yFyAb9nXesaKjTHksLi1VKe2izESWozYF
XnRtOgOW7/0xXcfK+7PW6xwcOqvTk61fqTGxj+iRyZf2e3FNtIB+T/Lg3SZF9szt
PM0jEUELWycC8l6WPTvzQjZZBCsF+cWbU1nxvRNQluzCsTDUEIfThJIFcLu0WkoQ
clUrC3d2tM8jclLPssb6/OV8GaJ+4mx4ri7HbGaUAOtA/TXKR6AuhgkRNPKYhpPU
0q/PRlGXdwJP8zXb8+CXMMTnI5Upur7Tc5T3I/x1Gqfz7n1sTRZfsuiQJ5uua4hz
4te3oV2tm7LWcNItHD43zttBTTx/m5icg71JE2gcr2oincw=
"@

# =============================================================================
# HELPERS
# =============================================================================

$utf8NoBom  = New-Object System.Text.UTF8Encoding($false)
$StepTotal  = 4
$StepFailed = 0

function Write-StepHeader {
    param([int]$Step, [string]$Label)
    Write-Host ""
    Write-Host "--- [$Step/$StepTotal] $Label ---" -ForegroundColor Cyan
}

function Write-OK   { param([string]$msg) Write-Host "      $msg" -ForegroundColor Green  }
function Write-Warn { param([string]$msg) Write-Host "      $msg" -ForegroundColor Yellow }
function Write-Err  { param([string]$msg) Write-Host "ERROR: $msg" -ForegroundColor Red   }

# =============================================================================
# MAIN
# =============================================================================

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Lab 3967 - VSI Post-Provisioning Setup"     -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# STEP 1 - IBM Internal Root CA
# ---------------------------------------------------------------------------
Write-StepHeader -Step 1 -Label "IBM Internal Root CA"
try {
    $certBytes = [Convert]::FromBase64String(($CertBase64 -replace '\s',''))
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
    $cert.Import($certBytes)

    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store(
        [System.Security.Cryptography.X509Certificates.StoreName]::Root,
        [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine
    )
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
    $existing = $store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    $store.Close()

    if ($existing) {
        Write-OK "Already installed - skipping."
    } else {
        $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        $store.Add($cert)
        $store.Close()
        Write-OK "Installed: $($cert.Subject)"
    }
} catch {
    Write-Err "Failed to install IBM Root CA: $_"
    $StepFailed++
}

# ---------------------------------------------------------------------------
# STEP 2 - Cisco Secure Client VPN Profile
# ---------------------------------------------------------------------------
Write-StepHeader -Step 2 -Label "Cisco Secure Client VPN"
try {
    if (-not (Get-Service -Name $VpnServiceName -ErrorAction SilentlyContinue)) {
        Write-Err "Service '$VpnServiceName' not found. Is Cisco Secure Client installed?"
        $StepFailed++
    } else {
        if (-not (Test-Path $VpnProfileDir)) {
            New-Item -ItemType Directory -Force -Path $VpnProfileDir | Out-Null
            Write-OK "Created profile directory."
        }

        $vpnXml = @"
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
"@
        $vpnFile = "$VpnProfileDir\Lab3967.xml"
        [System.IO.File]::WriteAllText($vpnFile, $vpnXml, $utf8NoBom)
        Write-OK "Profile written: $vpnFile"

        # Kill the AnyConnect UI process so it re-reads the profile on next launch.
        # csc_vpnagent is a protected service and cannot be stopped via SCM even as
        # Administrator - the profile file on disk is all that is needed.
        Get-Process -Name vpnui -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-OK "Profile written. Server: $VpnHostAddress"
        Write-OK "Open Cisco Secure Client - server will appear in the dropdown."
    }
} catch {
    Write-Err "Cisco VPN configuration failed: $_"
    $StepFailed++
}

# ---------------------------------------------------------------------------
# STEP 3 - Firefox Bookmarks Policy
# ---------------------------------------------------------------------------
Write-StepHeader -Step 3 -Label "Firefox Bookmarks"
try {
    $firefoxDir = @(
        "C:\Program Files\Mozilla Firefox",
        "C:\Program Files (x86)\Mozilla Firefox"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $firefoxDir) {
        Write-Err "Firefox not found. Please install Firefox first."
        $StepFailed++
    } else {
        # Close Firefox if running
        Stop-Process -Name firefox -Force -ErrorAction SilentlyContinue

        $policyDir = "$firefoxDir\distribution"
        if (-not (Test-Path $policyDir)) {
            New-Item -ItemType Directory -Force -Path $policyDir | Out-Null
        }

        $bookmarkList = $FirefoxBookmarks | ForEach-Object {
            [PSCustomObject]@{ Title = $_.Title; URL = $_.URL; Placement = "toolbar"; Folder = $FirefoxFolder }
        }
        $policyObject = [PSCustomObject]@{
            policies = [PSCustomObject]@{
                Bookmarks             = $bookmarkList
                DisplayBookmarksToolbar = "always"
            }
        }
        $policyJson = $policyObject | ConvertTo-Json -Depth 5
        $policyFile = "$policyDir\policies.json"
        [System.IO.File]::WriteAllText($policyFile, $policyJson, $utf8NoBom)
        Write-OK "Policy written: $policyFile"
        Write-OK "Folder '$FirefoxFolder' with $($FirefoxBookmarks.Count) bookmarks configured."
    }
} catch {
    Write-Err "Firefox bookmarks configuration failed: $_"
    $StepFailed++
}

# ---------------------------------------------------------------------------
# STEP 4 - PCOMM Session
# ---------------------------------------------------------------------------
Write-StepHeader -Step 4 -Label "PCOMM Session ($PCOMMSessionName)"
try {
    $pcommDir = @(
        "$env:ProgramFiles\IBM\Personal Communications",
        "${env:ProgramFiles(x86)}\IBM\Personal Communications"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $pcommDir) {
        Write-Err "IBM Personal Communications not found. Please install PCOMM first."
        $StepFailed++
    } else {
        # Resolve the interactive user's profile (works even when run as Administrator)
        $explorerProc = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" | Select-Object -First 1
        $ownerResult  = $explorerProc | Invoke-CimMethod -MethodName "GetOwner"
        if ($ownerResult -and $ownerResult.User) {
            $userProfile = "C:\Users\$($ownerResult.User)"
        } else {
            $userProfile = $env:USERPROFILE
        }

        $sessionDir = "$userProfile\AppData\Roaming\IBM\Personal Communications"
        if (-not (Test-Path $sessionDir)) {
            New-Item -ItemType Directory -Force -Path $sessionDir | Out-Null
        }

        $wsContent = @"
[Profile]
UID=$(([guid]::NewGuid()).ToString())
Version=9
ID=WS
[Telnet3270]
HostName=$PCOMMHost
HostPortNumber=$PCOMMPort
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
        $wsFile = "$sessionDir\$PCOMMSessionName.WS"
        [System.IO.File]::WriteAllText($wsFile, $wsContent, $utf8NoBom)
        Write-OK "Session written: $wsFile"
        Write-OK "Host: ${PCOMMHost}:${PCOMMPort} | TLS: Enabled"
    }
} catch {
    Write-Err "PCOMM session configuration failed: $_"
    $StepFailed++
}

# =============================================================================
# SUMMARY
# =============================================================================

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
if ($StepFailed -eq 0) {
    Write-Host " SUCCESS: All $StepTotal configurations applied." -ForegroundColor Green
} else {
    Write-Host " COMPLETED WITH $StepFailed FAILURE(S)."          -ForegroundColor Red
    Write-Host " Review errors above and re-run if needed."        -ForegroundColor Yellow
}
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# TECHZONE OUTPUT FILES
# post_deploy_text_output.txt  - rendered as Markdown on TechZone environment page
# post_deploy_json_output.json - shown as structured key/value pairs
# =============================================================================

$status = if ($StepFailed -eq 0) { "success" } else { "failed" }

$textOutput = @"
## Lab 3967 - VSI Setup $(if ($StepFailed -eq 0) { "Complete" } else { "Completed with Errors" })

| Configuration | Result |
|---|---|
| IBM Internal Root CA | $(if ($StepFailed -eq 0) { "Installed" } else { "See logs" }) |
| Cisco Secure Client VPN | $(if ($StepFailed -eq 0) { "Configured" } else { "See logs" }) |
| Firefox Bookmarks | $(if ($StepFailed -eq 0) { "Configured" } else { "See logs" }) |
| PCOMM Session ($PCOMMSessionName) | $(if ($StepFailed -eq 0) { "Created" } else { "See logs" }) |

**VPN Server:** $VpnHostAddress
**Mainframe Host:** ${PCOMMHost}:${PCOMMPort}
**Steps failed:** $StepFailed / $StepTotal
"@
$textOutput | Set-Content -Path ".\post_deploy_text_output.txt" -Encoding UTF8

$jsonOutput = @"
{
  "setup_status": "$status",
  "steps_total": $StepTotal,
  "steps_failed": $StepFailed,
  "vpn_server": "$VpnHostAddress",
  "mainframe_host": "$PCOMMHost",
  "mainframe_port": "$PCOMMPort",
  "pcomm_session": "$PCOMMSessionName"
}
"@
$jsonOutput | Set-Content -Path ".\post_deploy_json_output.json" -Encoding UTF8

exit $StepFailed
