package main

/*
Comprehensive Go cryptographic vulnerabilities for testing IBM Quantum Safe Explorer.
This file contains multiple quantum-vulnerable and weak cryptographic implementations.

WARNING: This code is intentionally insecure and should NOT be used in production!
*/

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/des"
	"crypto/dsa"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/md5"
	"crypto/rand"
	"crypto/rc4"
	"crypto/rsa"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"math/big"
	mathrand "math/rand"
	"time"
)

// ============================================================================
// CATEGORY 1: WEAK HASH ALGORITHMS
// ============================================================================

// WeakHashMD5 - Vulnerability: MD5 hash algorithm (broken, collision attacks)
func WeakHashMD5(data string) string {
	hash := md5.Sum([]byte(data))
	return hex.EncodeToString(hash[:])
}

// WeakHashSHA1 - Vulnerability: SHA-1 hash algorithm (deprecated, collision attacks)
func WeakHashSHA1(data string) string {
	hash := sha1.Sum([]byte(data))
	return hex.EncodeToString(hash[:])
}

// WeakPasswordHashMD5 - Vulnerability: Using MD5 for password hashing
func WeakPasswordHashMD5(password string) string {
	hash := md5.Sum([]byte(password))
	return hex.EncodeToString(hash[:])
}

// WeakPasswordHashSHA1 - Vulnerability: Using SHA-1 for password hashing
func WeakPasswordHashSHA1(password string) string {
	hash := sha1.Sum([]byte(password))
	return hex.EncodeToString(hash[:])
}

// ============================================================================
// CATEGORY 2: WEAK SYMMETRIC ENCRYPTION
// ============================================================================

// EncryptWithDES - Vulnerability: DES encryption (56-bit key, easily brute-forced)
func EncryptWithDES(plaintext string, key []byte) (string, error) {
	block, err := des.NewCipher(key[:8])
	if err != nil {
		return "", err
	}

	// Vulnerability: Using ECB mode (pattern leakage)
	ciphertext := make([]byte, len(plaintext))
	for i := 0; i < len(plaintext); i += 8 {
		block.Encrypt(ciphertext[i:], []byte(plaintext)[i:])
	}

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// EncryptWithTripleDES - Vulnerability: 3DES/Triple DES (quantum vulnerable)
func EncryptWithTripleDES(plaintext string, key []byte) (string, error) {
	block, err := des.NewTripleDESCipher(key[:24])
	if err != nil {
		return "", err
	}

	// Vulnerability: Using ECB mode
	ciphertext := make([]byte, len(plaintext))
	for i := 0; i < len(plaintext); i += 8 {
		block.Encrypt(ciphertext[i:], []byte(plaintext)[i:])
	}

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// EncryptWithRC4 - Vulnerability: RC4 stream cipher (biased, multiple attacks)
func EncryptWithRC4(plaintext string, key []byte) (string, error) {
	cipher, err := rc4.NewCipher(key)
	if err != nil {
		return "", err
	}

	ciphertext := make([]byte, len(plaintext))
	cipher.XORKeyStream(ciphertext, []byte(plaintext))

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// EncryptWithAESECB - Vulnerability: AES with ECB mode (pattern leakage)
func EncryptWithAESECB(plaintext string, key []byte) (string, error) {
	block, err := aes.NewCipher(key[:16])
	if err != nil {
		return "", err
	}

	// Vulnerability: ECB mode - patterns visible
	ciphertext := make([]byte, len(plaintext))
	for i := 0; i < len(plaintext); i += aes.BlockSize {
		block.Encrypt(ciphertext[i:], []byte(plaintext)[i:])
	}

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// EncryptWithStaticIV - Vulnerability: Using static/hardcoded IV
func EncryptWithStaticIV(plaintext string, key []byte) (string, error) {
	block, err := aes.NewCipher(key[:16])
	if err != nil {
		return "", err
	}

	// Vulnerability: Hardcoded IV - major security flaw
	staticIV := []byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
	stream := cipher.NewCFBEncrypter(block, staticIV)

	ciphertext := make([]byte, len(plaintext))
	stream.XORKeyStream(ciphertext, []byte(plaintext))

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// ============================================================================
// CATEGORY 3: WEAK ASYMMETRIC CRYPTOGRAPHY (QUANTUM VULNERABLE)
// ============================================================================

// GenerateRSA512 - Vulnerability: RSA with 512-bit key (extremely weak)
func GenerateRSA512() (*rsa.PrivateKey, error) {
	return rsa.GenerateKey(rand.Reader, 512)
}

// GenerateRSA1024 - Vulnerability: RSA with 1024-bit key (insufficient, quantum vulnerable)
func GenerateRSA1024() (*rsa.PrivateKey, error) {
	return rsa.GenerateKey(rand.Reader, 1024)
}

// GenerateRSA2048 - Vulnerability: RSA with 2048-bit key (quantum vulnerable)
func GenerateRSA2048() (*rsa.PrivateKey, error) {
	return rsa.GenerateKey(rand.Reader, 2048)
}

// SignWithRSA - Vulnerability: RSA signature (quantum vulnerable)
func SignWithRSA(message []byte, privateKey *rsa.PrivateKey) (string, error) {
	hashed := sha256.Sum256(message)
	signature, err := rsa.SignPKCS1v15(rand.Reader, privateKey, 0, hashed[:])
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(signature), nil
}

// GenerateDSAKey - Vulnerability: DSA key generation (quantum vulnerable)
func GenerateDSAKey() (*dsa.PrivateKey, error) {
	params := &dsa.Parameters{}
	// Vulnerability: DSA with L=1024, N=160 (weak)
	if err := dsa.GenerateParameters(params, rand.Reader, dsa.L1024N160); err != nil {
		return nil, err
	}

	privateKey := &dsa.PrivateKey{}
	privateKey.PublicKey.Parameters = *params
	if err := dsa.GenerateKey(privateKey, rand.Reader); err != nil {
		return nil, err
	}

	return privateKey, nil
}

// SignWithDSA - Vulnerability: DSA signature (quantum vulnerable)
func SignWithDSA(message []byte, privateKey *dsa.PrivateKey) (r, s *big.Int, err error) {
	hashed := sha256.Sum256(message)
	return dsa.Sign(rand.Reader, privateKey, hashed[:])
}

// GenerateECDSAP256 - Vulnerability: ECDSA P-256 curve (quantum vulnerable)
func GenerateECDSAP256() (*ecdsa.PrivateKey, error) {
	return ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
}

// GenerateECDSAP384 - Vulnerability: ECDSA P-384 curve (quantum vulnerable)
func GenerateECDSAP384() (*ecdsa.PrivateKey, error) {
	return ecdsa.GenerateKey(elliptic.P384(), rand.Reader)
}

// SignWithECDSA - Vulnerability: ECDSA signature (quantum vulnerable)
func SignWithECDSA(message []byte, privateKey *ecdsa.PrivateKey) (r, s *big.Int, err error) {
	hashed := sha256.Sum256(message)
	return ecdsa.Sign(rand.Reader, privateKey, hashed[:])
}

// ============================================================================
// CATEGORY 4: INSECURE RANDOM NUMBER GENERATION
// ============================================================================

// InsecureRandomMathRand - Vulnerability: Using math/rand for cryptographic purposes
func InsecureRandomMathRand() int {
	return mathrand.Intn(1000000)
}

// InsecureRandomWithSeed - Vulnerability: Using predictable seed
func InsecureRandomWithSeed() int {
	mathrand.Seed(12345) // Fixed seed - completely predictable
	return mathrand.Intn(1000000)
}

// InsecureRandomTimeSeed - Vulnerability: Using time as seed (predictable)
func InsecureRandomTimeSeed() int {
	mathrand.Seed(time.Now().UnixNano())
	return mathrand.Intn(1000000)
}

// InsecureKeyGeneration - Vulnerability: Generating cryptographic key with weak random
func InsecureKeyGeneration() []byte {
	mathrand.Seed(42)
	key := make([]byte, 16)
	for i := range key {
		key[i] = byte(mathrand.Intn(256))
	}
	return key
}

// ============================================================================
// CATEGORY 5: HARDCODED SECRETS
// ============================================================================

// Vulnerability: Hardcoded encryption key
var HardcodedKey = []byte("SuperSecretKey16")

// Vulnerability: Hardcoded IV
var HardcodedIV = []byte("InitVector123456")

// Vulnerability: Hardcoded password
const HardcodedPassword = "admin123"

// EncryptWithHardcodedKey - Vulnerability: Using hardcoded key for encryption
func EncryptWithHardcodedKey(plaintext string) (string, error) {
	block, err := aes.NewCipher(HardcodedKey)
	if err != nil {
		return "", err
	}

	stream := cipher.NewCFBEncrypter(block, HardcodedIV)
	ciphertext := make([]byte, len(plaintext))
	stream.XORKeyStream(ciphertext, []byte(plaintext))

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// ============================================================================
// CATEGORY 6: CERTIFICATE VULNERABILITIES
// ============================================================================

// GenerateWeakSelfSignedCert - Vulnerability: Self-signed cert with weak RSA
func GenerateWeakSelfSignedCert() error {
	// Vulnerability: Using weak RSA key
	privateKey, err := rsa.GenerateKey(rand.Reader, 1024)
	if err != nil {
		return err
	}

	template := x509.Certificate{
		SerialNumber: big.NewInt(1),
		// Vulnerability: Using SHA-1 for signature
		// (implied by weak key and old practices)
	}

	_, err = x509.CreateCertificate(rand.Reader, &template, &template, &privateKey.PublicKey, privateKey)
	return err
}

// ============================================================================
// CATEGORY 7: MULTIPLE COMBINED VULNERABILITIES
// ============================================================================

// MultipleVulnerabilities - Multiple vulnerabilities combined
func MultipleVulnerabilities(plaintext string) (string, error) {
	// Vulnerability 1: Weak random number generation
	mathrand.Seed(123)
	key := make([]byte, 8)
	for i := range key {
		key[i] = byte(mathrand.Intn(256))
	}

	// Vulnerability 2: Weak algorithm (DES)
	block, err := des.NewCipher(key)
	if err != nil {
		return "", err
	}

	// Vulnerability 3: ECB mode
	ciphertext := make([]byte, len(plaintext))
	for i := 0; i < len(plaintext); i += 8 {
		block.Encrypt(ciphertext[i:], []byte(plaintext)[i:])
	}

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// ============================================================================
// MAIN DEMONSTRATION
// ============================================================================

func main() {
	fmt.Println("=" + string(make([]byte, 69)) + "=")
	fmt.Println("CRYPTOGRAPHIC VULNERABILITIES TEST - IBM Quantum Safe Explorer")
	fmt.Println("=" + string(make([]byte, 69)) + "=")

	testData := "Sensitive Information"
	testPassword := "password123"

	fmt.Println("\n[1] WEAK HASH ALGORITHMS:")
	fmt.Printf("   MD5 Hash: %s\n", WeakHashMD5(testData))
	fmt.Printf("   SHA-1 Hash: %s\n", WeakHashSHA1(testData))
	fmt.Printf("   MD5 Password Hash: %s\n", WeakPasswordHashMD5(testPassword))

	fmt.Println("\n[2] WEAK SYMMETRIC ENCRYPTION:")
	desKey := []byte("8bytekey")
	if encrypted, err := EncryptWithDES(testData, desKey); err == nil {
		fmt.Printf("   DES Encrypted: %s\n", encrypted)
	}

	tripleDesKey := []byte("24ByteKeyForTripleDES123")
	if encrypted, err := EncryptWithTripleDES(testData, tripleDesKey); err == nil {
		fmt.Printf("   3DES Encrypted: %s\n", encrypted)
	}

	if encrypted, err := EncryptWithRC4(testData, desKey); err == nil {
		fmt.Printf("   RC4 Encrypted: %s\n", encrypted)
	}

	fmt.Println("\n[3] QUANTUM-VULNERABLE ASYMMETRIC CRYPTO:")
	if rsa512, err := GenerateRSA512(); err == nil {
		fmt.Printf("   RSA-512 key generated: %d bits\n", rsa512.N.BitLen())
	}

	if rsa1024, err := GenerateRSA1024(); err == nil {
		fmt.Printf("   RSA-1024 key generated: %d bits\n", rsa1024.N.BitLen())
	}

	if rsa2048, err := GenerateRSA2048(); err == nil {
		fmt.Printf("   RSA-2048 key generated: %d bits\n", rsa2048.N.BitLen())
	}

	if _, err := GenerateDSAKey(); err == nil {
		fmt.Println("   DSA key generated")
	}

	if ecdsaKey, err := GenerateECDSAP256(); err == nil {
		fmt.Printf("   ECDSA P-256 key generated: %s\n", ecdsaKey.Curve.Params().Name)
	}

	fmt.Println("\n[4] INSECURE RANDOM NUMBER GENERATION:")
	fmt.Printf("   Insecure random: %d\n", InsecureRandomMathRand())
	fmt.Printf("   Predictable seed random: %d\n", InsecureRandomWithSeed())
	fmt.Printf("   Time-based seed random: %d\n", InsecureRandomTimeSeed())

	fmt.Println("\n[5] HARDCODED SECRETS:")
	fmt.Printf("   Hardcoded key: %s\n", string(HardcodedKey))
	if encrypted, err := EncryptWithHardcodedKey(testData); err == nil {
		fmt.Printf("   Encrypted with hardcoded key: %s\n", encrypted)
	}

	fmt.Println("\n[6] COMBINED VULNERABILITIES:")
	if encrypted, err := MultipleVulnerabilities(testData); err == nil {
		fmt.Printf("   Multiple vulnerabilities: %s\n", encrypted)
	}

	fmt.Println("\n" + "=" + string(make([]byte, 69)) + "=")
	fmt.Println("All vulnerability tests completed!")
	fmt.Println("This file should trigger multiple findings in Quantum Safe Explorer!")
	fmt.Println("=" + string(make([]byte, 69)) + "=")
}

// Made with Bob