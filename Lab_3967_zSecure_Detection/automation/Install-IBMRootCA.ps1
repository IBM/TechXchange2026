# =============================================================================
# Install-IBMRootCA.ps1
# Lab 3967 - zSecure Detection | TechXChange 2026
#
# PURPOSE : Silently installs the IBM Internal Root CA certificate into the
#           Windows Trusted Root Certification Authorities store (LocalMachine).
#           Required for PCOMM and browser trust of IBM lab endpoints.
#
# RUN AS  : Administrator
# USAGE   : PowerShell -ExecutionPolicy Bypass -File .\Install-IBMRootCA.ps1
# =============================================================================

# --- Enforce Administrator ---------------------------------------------------
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host ""
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    exit 1
}

# --- Certificate (IBM Internal Root CA) --------------------------------------
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
# -----------------------------------------------------------------------------

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Lab 3967 - IBM Root CA Certificate Install" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Decode the certificate
Write-Host "[1/4] Decoding certificate..." -ForegroundColor Yellow
try {
    $certBytes = [Convert]::FromBase64String(($CertBase64 -replace '\s',''))
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
    $cert.Import($certBytes)
    Write-Host "      Subject : $($cert.Subject)" -ForegroundColor Green
    Write-Host "      Issuer  : $($cert.Issuer)"  -ForegroundColor Green
    Write-Host "      Expires : $($cert.NotAfter)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to decode certificate: $_" -ForegroundColor Red
    exit 1
}

# Step 2 - Check if already installed
Write-Host "[2/4] Checking if already installed..." -ForegroundColor Yellow
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    [System.Security.Cryptography.X509Certificates.StoreName]::Root,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine
)
$store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
$existing = $store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
$store.Close()

if ($existing) {
    Write-Host "      Already installed (thumbprint match). Nothing to do." -ForegroundColor Green
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host " Certificate is already trusted."             -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}
Write-Host "      Not yet installed." -ForegroundColor Green

# Step 3 - Install into Trusted Root CA store
Write-Host "[3/4] Installing certificate..." -ForegroundColor Yellow
try {
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $store.Add($cert)
    $store.Close()
    Write-Host "      Installed into LocalMachine\Root." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to install certificate: $_" -ForegroundColor Red
    exit 1
}

# Step 4 - Verify installation
Write-Host "[4/4] Verifying installation..." -ForegroundColor Yellow
$store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
$installed = $store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
$store.Close()

if (-not $installed) {
    Write-Host "ERROR: Certificate not found in store after install." -ForegroundColor Red
    exit 1
}
Write-Host "      Verification passed." -ForegroundColor Green

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " SUCCESS: IBM Internal Root CA trusted."      -ForegroundColor Green
Write-Host " Thumbprint: $($cert.Thumbprint)"             -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
