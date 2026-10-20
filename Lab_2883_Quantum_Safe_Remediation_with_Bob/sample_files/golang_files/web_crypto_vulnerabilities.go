package main

/*
Go Web Service Cryptographic Vulnerabilities
Testing file for IBM Quantum Safe Explorer

WARNING: This code is intentionally insecure and should NOT be used in production!
*/

import (
	"crypto/md5"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"math/big"
	mathrand "math/rand"
	"time"
)

// ============================================================================
// JWT VULNERABILITIES
// ============================================================================

// InsecureJWTHandler - Vulnerability: Weak JWT implementation
type InsecureJWTHandler struct {
	// Vulnerability: Weak secret key
	Secret string
}

// NewInsecureJWTHandler creates a handler with weak secret
func NewInsecureJWTHandler() *InsecureJWTHandler {
	return &InsecureJWTHandler{
		Secret: "weak_secret", // Vulnerability: Hardcoded weak secret
	}
}

// CreateJWTNoneAlgorithm - Vulnerability: JWT with 'none' algorithm
func (h *InsecureJWTHandler) CreateJWTNoneAlgorithm(userID int) string {
	header := base64.StdEncoding.EncodeToString([]byte(`{"alg":"none","typ":"JWT"}`))
	payload := base64.StdEncoding.EncodeToString([]byte(fmt.Sprintf(`{"user_id":%d}`, userID)))
	return fmt.Sprintf("%s.%s.", header, payload)
}

// CreateJWTWeakSecret - Vulnerability: JWT with weak secret
func (h *InsecureJWTHandler) CreateJWTWeakSecret(userID int) string {
	// Vulnerability: Using MD5 for HMAC
	data := fmt.Sprintf(`{"user_id":%d}`, userID)
	hash := md5.Sum([]byte(h.Secret + data))
	signature := base64.StdEncoding.EncodeToString(hash[:])
	return fmt.Sprintf("header.%s.%s", base64.StdEncoding.EncodeToString([]byte(data)), signature)
}

// CreateJWTRSAWeak - Vulnerability: JWT with RSA (quantum vulnerable)
func (h *InsecureJWTHandler) CreateJWTRSAWeak(userID int) (string, error) {
	// Vulnerability: Using weak RSA key
	privateKey, err := rsa.GenerateKey(rand.Reader, 1024)
	if err != nil {
		return "", err
	}

	data := []byte(fmt.Sprintf(`{"user_id":%d}`, userID))
	hashed := sha256.Sum256(data)
	signature, err := rsa.SignPKCS1v15(rand.Reader, privateKey, 0, hashed[:])
	if err != nil {
		return "", err
	}

	return base64.StdEncoding.EncodeToString(signature), nil
}

// ============================================================================
// SESSION MANAGEMENT VULNERABILITIES
// ============================================================================

// InsecureSessionManager - Vulnerability: Weak session management
type InsecureSessionManager struct {
	// Vulnerability: Hardcoded secret
	SecretKey string
}

// NewInsecureSessionManager creates a session manager with hardcoded secret
func NewInsecureSessionManager() *InsecureSessionManager {
	return &InsecureSessionManager{
		SecretKey: "hardcoded-session-secret", // Vulnerability
	}
}

// CreateSessionTokenWeak - Vulnerability: Weak session token generation
func (sm *InsecureSessionManager) CreateSessionTokenWeak(userID int) string {
	mathrand.Seed(int64(userID)) // Vulnerability: Predictable seed
	token := make([]byte, 32)
	for i := range token {
		token[i] = byte(mathrand.Intn(256))
	}
	return hex.EncodeToString(token)
}

// SignSessionDataMD5 - Vulnerability: Using MD5 for HMAC
func (sm *InsecureSessionManager) SignSessionDataMD5(data string) string {
	hash := md5.Sum([]byte(sm.SecretKey + data))
	return hex.EncodeToString(hash[:])
}

// SignSessionDataSHA1 - Vulnerability: Using SHA-1 for HMAC
func (sm *InsecureSessionManager) SignSessionDataSHA1(data string) string {
	hash := sha1.Sum([]byte(sm.SecretKey + data))
	return hex.EncodeToString(hash[:])
}

// ============================================================================
// API KEY GENERATION VULNERABILITIES
// ============================================================================

// InsecureAPIKeyGenerator - Vulnerability: Weak API key generation
type InsecureAPIKeyGenerator struct{}

// GenerateAPIKeyWeakRandom - Vulnerability: Using weak random for API keys
func (g *InsecureAPIKeyGenerator) GenerateAPIKeyWeakRandom() string {
	mathrand.Seed(time.Now().UnixNano()) // Vulnerability: Predictable
	key := make([]byte, 32)
	for i := range key {
		key[i] = byte(mathrand.Intn(256))
	}
	return hex.EncodeToString(key)
}

// GenerateAPIKeyPredictable - Vulnerability: Predictable API key based on user ID
func (g *InsecureAPIKeyGenerator) GenerateAPIKeyPredictable(userID int) string {
	data := fmt.Sprintf("api_key_%d", userID)
	hash := md5.Sum([]byte(data))
	return hex.EncodeToString(hash[:])
}

// GenerateAPIKeySequential - Vulnerability: Sequential API keys
func (g *InsecureAPIKeyGenerator) GenerateAPIKeySequential(counter int) string {
	return fmt.Sprintf("API-%08d", counter)
}

// ============================================================================
// PASSWORD HASHING VULNERABILITIES
// ============================================================================

// InsecurePasswordHasher - Vulnerability: Weak password hashing
type InsecurePasswordHasher struct{}

// HashPasswordMD5 - Vulnerability: MD5 for password hashing
func (ph *InsecurePasswordHasher) HashPasswordMD5(password string) string {
	hash := md5.Sum([]byte(password))
	return hex.EncodeToString(hash[:])
}

// HashPasswordSHA1 - Vulnerability: SHA-1 for password hashing
func (ph *InsecurePasswordHasher) HashPasswordSHA1(password string) string {
	hash := sha1.Sum([]byte(password))
	return hex.EncodeToString(hash[:])
}

// HashPasswordMD5WithSalt - Vulnerability: MD5 with weak salt
func (ph *InsecurePasswordHasher) HashPasswordMD5WithSalt(password string) string {
	mathrand.Seed(time.Now().UnixNano())
	salt := fmt.Sprintf("%d", mathrand.Intn(10000)) // Weak salt
	hash := md5.Sum([]byte(salt + password))
	return fmt.Sprintf("%s:%s", salt, hex.EncodeToString(hash[:]))
}

// VerifyPasswordTimingAttack - Vulnerability: Timing attack in password verification
func (ph *InsecurePasswordHasher) VerifyPasswordTimingAttack(password, hashed string) bool {
	return ph.HashPasswordMD5(password) == hashed // Not constant-time
}

// ============================================================================
// PASSWORD RESET TOKEN VULNERABILITIES
// ============================================================================

// InsecurePasswordResetHandler - Vulnerability: Weak password reset tokens
type InsecurePasswordResetHandler struct{}

// GenerateResetTokenWeak - Vulnerability: Predictable reset token
func (h *InsecurePasswordResetHandler) GenerateResetTokenWeak(email string) string {
	timestamp := time.Now().Unix()
	data := fmt.Sprintf("%s%d", email, timestamp)
	hash := md5.Sum([]byte(data))
	return hex.EncodeToString(hash[:])
}

// GenerateResetTokenNoExpiry - Vulnerability: Reset token without expiration
func (h *InsecurePasswordResetHandler) GenerateResetTokenNoExpiry(userID int) string {
	mathrand.Seed(int64(userID))
	token := make([]byte, 6)
	for i := range token {
		token[i] = byte('0' + mathrand.Intn(10))
	}
	return string(token)
}

// VerifyResetTokenTiming - Vulnerability: Timing attack in token verification
func (h *InsecurePasswordResetHandler) VerifyResetTokenTiming(token, expected string) bool {
	return token == expected // Not constant-time comparison
}

// ============================================================================
// TWO-FACTOR AUTHENTICATION VULNERABILITIES
// ============================================================================

// Insecure2FAHandler - Vulnerability: Weak 2FA implementation
type Insecure2FAHandler struct{}

// GenerateTOTPSecretWeak - Vulnerability: Weak TOTP secret generation
func (h *Insecure2FAHandler) GenerateTOTPSecretWeak() string {
	mathrand.Seed(42) // Vulnerability: Fixed seed
	secret := make([]byte, 10)
	for i := range secret {
		secret[i] = byte(mathrand.Intn(256))
	}
	return base64.StdEncoding.EncodeToString(secret)
}

// GenerateBackupCodesWeak - Vulnerability: Weak backup code generation
func (h *Insecure2FAHandler) GenerateBackupCodesWeak(count int) []string {
	mathrand.Seed(time.Now().UnixNano())
	codes := make([]string, count)
	for i := 0; i < count; i++ {
		code := make([]byte, 8)
		for j := range code {
			code[j] = byte('0' + mathrand.Intn(10))
		}
		codes[i] = string(code)
	}
	return codes
}

// Verify2FACodeTiming - Vulnerability: Timing attack in 2FA verification
func (h *Insecure2FAHandler) Verify2FACodeTiming(code, expected string) bool {
	return code == expected // Not constant-time
}

// ============================================================================
// OAUTH/OPENID VULNERABILITIES
// ============================================================================

// InsecureOAuthHandler - Vulnerability: Weak OAuth implementation
type InsecureOAuthHandler struct{}

// GenerateStateParameterWeak - Vulnerability: Weak OAuth state parameter
func (h *InsecureOAuthHandler) GenerateStateParameterWeak() string {
	mathrand.Seed(time.Now().UnixNano())
	state := make([]byte, 16)
	for i := range state {
		state[i] = byte('0' + mathrand.Intn(10))
	}
	return string(state)
}

// GenerateClientSecretWeak - Vulnerability: Predictable client secret
func (h *InsecureOAuthHandler) GenerateClientSecretWeak(clientID string) string {
	data := fmt.Sprintf("client_%s", clientID)
	hash := md5.Sum([]byte(data))
	return hex.EncodeToString(hash[:])
}

// GenerateAuthorizationCodeWeak - Vulnerability: Weak authorization code
func (h *InsecureOAuthHandler) GenerateAuthorizationCodeWeak(userID int) string {
	mathrand.Seed(int64(userID))
	code := make([]byte, 32)
	for i := range code {
		code[i] = byte(mathrand.Intn(256))
	}
	return hex.EncodeToString(code)
}

// ============================================================================
// COOKIE SECURITY VULNERABILITIES
// ============================================================================

// InsecureCookieHandler - Vulnerability: Insecure cookie handling
type InsecureCookieHandler struct {
	// Vulnerability: Hardcoded encryption key
	EncryptionKey []byte
}

// NewInsecureCookieHandler creates a handler with hardcoded key
func NewInsecureCookieHandler() *InsecureCookieHandler {
	return &InsecureCookieHandler{
		EncryptionKey: []byte("CookieKey1234567"), // Vulnerability
	}
}

// EncryptCookieWeak - Vulnerability: Weak cookie encryption
func (h *InsecureCookieHandler) EncryptCookieWeak(value string) string {
	// Vulnerability: Simple XOR (extremely weak)
	encrypted := make([]byte, len(value))
	for i := 0; i < len(value); i++ {
		encrypted[i] = value[i] ^ h.EncryptionKey[i%len(h.EncryptionKey)]
	}
	return base64.StdEncoding.EncodeToString(encrypted)
}

// SignCookieMD5 - Vulnerability: Using MD5 for cookie signature
func (h *InsecureCookieHandler) SignCookieMD5(value string) string {
	hash := md5.Sum([]byte(string(h.EncryptionKey) + value))
	return hex.EncodeToString(hash[:])
}

// ============================================================================
// CERTIFICATE PINNING VULNERABILITIES
// ============================================================================

// InsecureCertificateHandler - Vulnerability: Weak certificate handling
type InsecureCertificateHandler struct{}

// GenerateWeakCertificateFingerprint - Vulnerability: Using MD5 for cert fingerprint
func (h *InsecureCertificateHandler) GenerateWeakCertificateFingerprint(certData []byte) string {
	hash := md5.Sum(certData)
	return hex.EncodeToString(hash[:])
}

// GenerateSHA1CertificateFingerprint - Vulnerability: Using SHA-1 for cert fingerprint
func (h *InsecureCertificateHandler) GenerateSHA1CertificateFingerprint(certData []byte) string {
	hash := sha1.Sum(certData)
	return hex.EncodeToString(hash[:])
}

// ============================================================================
// RATE LIMITING TOKEN VULNERABILITIES
// ============================================================================

// InsecureRateLimiter - Vulnerability: Weak rate limiting tokens
type InsecureRateLimiter struct{}

// GenerateRateLimitTokenWeak - Vulnerability: Predictable rate limit token
func (rl *InsecureRateLimiter) GenerateRateLimitTokenWeak(clientIP string) string {
	timestamp := time.Now().Unix()
	data := fmt.Sprintf("%s:%d", clientIP, timestamp)
	hash := md5.Sum([]byte(data))
	return hex.EncodeToString(hash[:])
}

// ============================================================================
// MAIN DEMONSTRATION
// ============================================================================

func main() {
	fmt.Println("======================================================================")
	fmt.Println("WEB SERVICE CRYPTO VULNERABILITIES - IBM Quantum Safe Explorer")
	fmt.Println("======================================================================")

	// JWT vulnerabilities
	fmt.Println("\n[1] JWT VULNERABILITIES:")
	jwtHandler := NewInsecureJWTHandler()
	fmt.Printf("   JWT with 'none' algorithm: %s\n", jwtHandler.CreateJWTNoneAlgorithm(12345))
	fmt.Printf("   JWT with weak secret: %s\n", jwtHandler.CreateJWTWeakSecret(12345))

	// Session management vulnerabilities
	fmt.Println("\n[2] SESSION MANAGEMENT VULNERABILITIES:")
	sessionMgr := NewInsecureSessionManager()
	fmt.Printf("   Weak Session Token: %s\n", sessionMgr.CreateSessionTokenWeak(12345))
	fmt.Printf("   MD5 HMAC: %s\n", sessionMgr.SignSessionDataMD5("session_data"))

	// API key vulnerabilities
	fmt.Println("\n[3] API KEY GENERATION VULNERABILITIES:")
	apiGen := &InsecureAPIKeyGenerator{}
	fmt.Printf("   Weak Random API Key: %s\n", apiGen.GenerateAPIKeyWeakRandom())
	fmt.Printf("   Predictable API Key: %s\n", apiGen.GenerateAPIKeyPredictable(12345))

	// Password hashing vulnerabilities
	fmt.Println("\n[4] PASSWORD HASHING VULNERABILITIES:")
	pwHasher := &InsecurePasswordHasher{}
	fmt.Printf("   MD5 Password Hash: %s\n", pwHasher.HashPasswordMD5("password123"))
	fmt.Printf("   SHA-1 Password Hash: %s\n", pwHasher.HashPasswordSHA1("password123"))

	// Password reset vulnerabilities
	fmt.Println("\n[5] PASSWORD RESET TOKEN VULNERABILITIES:")
	resetHandler := &InsecurePasswordResetHandler{}
	fmt.Printf("   Weak Reset Token: %s\n", resetHandler.GenerateResetTokenWeak("user@example.com"))

	// 2FA vulnerabilities
	fmt.Println("\n[6] TWO-FACTOR AUTHENTICATION VULNERABILITIES:")
	twoFAHandler := &Insecure2FAHandler{}
	fmt.Printf("   Weak TOTP Secret: %s\n", twoFAHandler.GenerateTOTPSecretWeak())
	fmt.Printf("   Weak Backup Codes: %v\n", twoFAHandler.GenerateBackupCodesWeak(5))

	// OAuth vulnerabilities
	fmt.Println("\n[7] OAUTH VULNERABILITIES:")
	oauthHandler := &InsecureOAuthHandler{}
	fmt.Printf("   Weak State Parameter: %s\n", oauthHandler.GenerateStateParameterWeak())
	fmt.Printf("   Weak Client Secret: %s\n", oauthHandler.GenerateClientSecretWeak("client123"))

	// Cookie vulnerabilities
	fmt.Println("\n[8] COOKIE SECURITY VULNERABILITIES:")
	cookieHandler := NewInsecureCookieHandler()
	fmt.Printf("   Weak Cookie Encryption: %s\n", cookieHandler.EncryptCookieWeak("session_data"))
	fmt.Printf("   MD5 Cookie Signature: %s\n", cookieHandler.SignCookieMD5("session_data"))

	fmt.Println("\n======================================================================")
	fmt.Println("All web service vulnerability tests completed!")
	fmt.Println("This file should trigger multiple findings in Quantum Safe Explorer!")
	fmt.Println("======================================================================")
}

// Made with Bob