#include <iostream>
#include <cstring>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/dsa.h>
#include <openssl/ec.h>
#include <openssl/md5.h>
#include <openssl/sha.h>
#include <openssl/des.h>
#include <openssl/rc4.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/rand.h>

/*
 * Comprehensive C++ OpenSSL Cryptographic Vulnerabilities
 * Testing file for IBM Quantum Safe Explorer
 * 
 * WARNING: This code is intentionally insecure and should NOT be used in production!
 */

// ============================================================================
// CATEGORY 1: WEAK HASH ALGORITHMS
// ============================================================================

/**
 * Vulnerability: MD5 hash algorithm (broken, collision attacks)
 */
void weakHashMD5(const std::string& data) {
    unsigned char digest[MD5_DIGEST_LENGTH];
    MD5(reinterpret_cast<const unsigned char*>(data.c_str()), data.size(), digest);
    
    std::cout << "MD5 Hash: ";
    for (int i = 0; i < MD5_DIGEST_LENGTH; i++)
        printf("%02x", digest[i]);
    std::cout << std::endl;
}

/**
 * Vulnerability: SHA-1 hash algorithm (deprecated, collision attacks)
 */
void weakHashSHA1(const std::string& data) {
    unsigned char digest[SHA_DIGEST_LENGTH];
    SHA1(reinterpret_cast<const unsigned char*>(data.c_str()), data.size(), digest);
    
    std::cout << "SHA-1 Hash: ";
    for (int i = 0; i < SHA_DIGEST_LENGTH; i++)
        printf("%02x", digest[i]);
    std::cout << std::endl;
}

/**
 * Vulnerability: MD5 for password hashing
 */
void weakPasswordHashMD5(const std::string& password) {
    unsigned char digest[MD5_DIGEST_LENGTH];
    MD5(reinterpret_cast<const unsigned char*>(password.c_str()), password.size(), digest);
    
    std::cout << "MD5 Password Hash: ";
    for (int i = 0; i < MD5_DIGEST_LENGTH; i++)
        printf("%02x", digest[i]);
    std::cout << std::endl;
}

// ============================================================================
// CATEGORY 2: WEAK SYMMETRIC ENCRYPTION
// ============================================================================

/**
 * Vulnerability: DES encryption (56-bit key, easily brute-forced)
 */
void encryptWithDES(const std::string& plaintext) {
    // Vulnerability: Hardcoded key
    unsigned char key[8] = {0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF};
    DES_key_schedule schedule;
    DES_set_key_unchecked((const_DES_cblock*)key, &schedule);
    
    unsigned char input[8] = {0};
    unsigned char output[8] = {0};
    strncpy((char*)input, plaintext.c_str(), 8);
    
    // Vulnerability: DES encryption
    DES_ecb_encrypt((const_DES_cblock*)input, (DES_cblock*)output, &schedule, DES_ENCRYPT);
    
    std::cout << "DES Encrypted: ";
    for (int i = 0; i < 8; i++)
        printf("%02x", output[i]);
    std::cout << std::endl;
}

/**
 * Vulnerability: 3DES/Triple DES (quantum vulnerable)
 */
void encryptWith3DES(const std::string& plaintext) {
    // Vulnerability: Hardcoded keys
    unsigned char key1[8] = {0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF};
    unsigned char key2[8] = {0xFE, 0xDC, 0xBA, 0x98, 0x76, 0x54, 0x32, 0x10};
    unsigned char key3[8] = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88};
    
    DES_key_schedule ks1, ks2, ks3;
    DES_set_key_unchecked((const_DES_cblock*)key1, &ks1);
    DES_set_key_unchecked((const_DES_cblock*)key2, &ks2);
    DES_set_key_unchecked((const_DES_cblock*)key3, &ks3);
    
    unsigned char input[8] = {0};
    unsigned char output[8] = {0};
    strncpy((char*)input, plaintext.c_str(), 8);
    
    // Vulnerability: 3DES encryption
    DES_ecb3_encrypt((const_DES_cblock*)input, (DES_cblock*)output, &ks1, &ks2, &ks3, DES_ENCRYPT);
    
    std::cout << "3DES Encrypted: ";
    for (int i = 0; i < 8; i++)
        printf("%02x", output[i]);
    std::cout << std::endl;
}

/**
 * Vulnerability: RC4 stream cipher (biased, multiple attacks)
 */
void encryptWithRC4(const std::string& plaintext) {
    // Vulnerability: Hardcoded key
    unsigned char key[16] = "WeakRC4Key12345";
    RC4_KEY rc4_key;
    RC4_set_key(&rc4_key, 16, key);
    
    unsigned char output[256] = {0};
    RC4(&rc4_key, plaintext.size(), 
        reinterpret_cast<const unsigned char*>(plaintext.c_str()), output);
    
    std::cout << "RC4 Encrypted: ";
    for (size_t i = 0; i < plaintext.size(); i++)
        printf("%02x", output[i]);
    std::cout << std::endl;
}

/**
 * Vulnerability: AES with ECB mode (pattern leakage)
 */
void encryptWithAESECB(const std::string& plaintext) {
    // Vulnerability: Hardcoded key
    unsigned char key[16] = "AESKey1234567890";
    
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    // Vulnerability: ECB mode
    EVP_EncryptInit_ex(ctx, EVP_aes_128_ecb(), NULL, key, NULL);
    
    unsigned char ciphertext[128];
    int len;
    EVP_EncryptUpdate(ctx, ciphertext, &len, 
        reinterpret_cast<const unsigned char*>(plaintext.c_str()), plaintext.size());
    
    int ciphertext_len = len;
    EVP_EncryptFinal_ex(ctx, ciphertext + len, &len);
    ciphertext_len += len;
    
    EVP_CIPHER_CTX_free(ctx);
    
    std::cout << "AES-ECB Encrypted: ";
    for (int i = 0; i < ciphertext_len; i++)
        printf("%02x", ciphertext[i]);
    std::cout << std::endl;
}

/**
 * Vulnerability: Static/hardcoded IV
 */
void encryptWithStaticIV(const std::string& plaintext) {
    // Vulnerability: Hardcoded key and IV
    unsigned char key[16] = "AESKey1234567890";
    unsigned char iv[16] = {0}; // All zeros - major security flaw
    
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, key, iv);
    
    unsigned char ciphertext[128];
    int len;
    EVP_EncryptUpdate(ctx, ciphertext, &len, 
        reinterpret_cast<const unsigned char*>(plaintext.c_str()), plaintext.size());
    
    int ciphertext_len = len;
    EVP_EncryptFinal_ex(ctx, ciphertext + len, &len);
    ciphertext_len += len;
    
    EVP_CIPHER_CTX_free(ctx);
    
    std::cout << "AES-CBC with static IV: ";
    for (int i = 0; i < ciphertext_len; i++)
        printf("%02x", ciphertext[i]);
    std::cout << std::endl;
}

// ============================================================================
// CATEGORY 3: WEAK ASYMMETRIC CRYPTOGRAPHY (QUANTUM VULNERABLE)
// ============================================================================

/**
 * Vulnerability: RSA with 512-bit key (extremely weak)
 */
void generateRSA512() {
    RSA *rsa = RSA_new();
    BIGNUM *e = BN_new();
    BN_set_word(e, RSA_F4);
    
    // Vulnerability: 512-bit RSA key
    RSA_generate_key_ex(rsa, 512, e, NULL);
    
    std::cout << "RSA-512 key generated: " << RSA_size(rsa) * 8 << " bits" << std::endl;
    
    BN_free(e);
    RSA_free(rsa);
}

/**
 * Vulnerability: RSA with 1024-bit key (insufficient, quantum vulnerable)
 */
void generateRSA1024() {
    RSA *rsa = RSA_new();
    BIGNUM *e = BN_new();
    BN_set_word(e, RSA_F4);
    
    // Vulnerability: 1024-bit RSA key
    RSA_generate_key_ex(rsa, 1024, e, NULL);
    
    std::cout << "RSA-1024 key generated: " << RSA_size(rsa) * 8 << " bits" << std::endl;
    
    BN_free(e);
    RSA_free(rsa);
}

/**
 * Vulnerability: RSA with 2048-bit key (quantum vulnerable)
 */
void generateRSA2048() {
    RSA *rsa = RSA_new();
    BIGNUM *e = BN_new();
    BN_set_word(e, RSA_F4);
    
    // Vulnerability: 2048-bit RSA key (quantum vulnerable)
    RSA_generate_key_ex(rsa, 2048, e, NULL);
    
    std::cout << "RSA-2048 key generated: " << RSA_size(rsa) * 8 << " bits" << std::endl;
    
    BN_free(e);
    RSA_free(rsa);
}

/**
 * Vulnerability: DSA key generation (quantum vulnerable)
 */
void generateDSA1024() {
    DSA *dsa = DSA_new();
    
    // Vulnerability: DSA with 1024-bit key
    DSA_generate_parameters_ex(dsa, 1024, NULL, 0, NULL, NULL, NULL);
    DSA_generate_key(dsa);
    
    std::cout << "DSA-1024 key generated" << std::endl;
    
    DSA_free(dsa);
}

/**
 * Vulnerability: ECDSA P-256 curve (quantum vulnerable)
 */
void generateECDSAP256() {
    EC_KEY *ec_key = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
    EC_KEY_generate_key(ec_key);
    
    std::cout << "ECDSA P-256 key generated" << std::endl;
    
    EC_KEY_free(ec_key);
}

/**
 * Vulnerability: ECDSA P-384 curve (quantum vulnerable)
 */
void generateECDSAP384() {
    EC_KEY *ec_key = EC_KEY_new_by_curve_name(NID_secp384r1);
    EC_KEY_generate_key(ec_key);
    
    std::cout << "ECDSA P-384 key generated" << std::endl;
    
    EC_KEY_free(ec_key);
}

// ============================================================================
// CATEGORY 4: INSECURE RANDOM NUMBER GENERATION
// ============================================================================

/**
 * Vulnerability: Using C rand() for cryptographic purposes
 */
void insecureRandomCRand() {
    srand(time(NULL)); // Predictable seed
    int random_value = rand();
    std::cout << "Insecure random (C rand): " << random_value << std::endl;
}

/**
 * Vulnerability: Using predictable seed
 */
void insecureRandomPredictableSeed() {
    srand(12345); // Fixed seed - completely predictable
    int random_value = rand();
    std::cout << "Predictable seed random: " << random_value << std::endl;
}

/**
 * Vulnerability: Weak random for key generation
 */
void insecureKeyGeneration() {
    srand(42);
    unsigned char key[16];
    for (int i = 0; i < 16; i++) {
        key[i] = rand() % 256;
    }
    
    std::cout << "Insecure key: ";
    for (int i = 0; i < 16; i++)
        printf("%02x", key[i]);
    std::cout << std::endl;
}

// ============================================================================
// CATEGORY 5: HARDCODED SECRETS
// ============================================================================

// Vulnerability: Hardcoded encryption key
const unsigned char HARDCODED_KEY[16] = "HardcodedKey1234";

// Vulnerability: Hardcoded IV
const unsigned char HARDCODED_IV[16] = "HardcodedIV12345";

// Vulnerability: Hardcoded password
const char* HARDCODED_PASSWORD = "admin123";

/**
 * Vulnerability: Using hardcoded key for encryption
 */
void encryptWithHardcodedKey(const std::string& plaintext) {
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, HARDCODED_KEY, HARDCODED_IV);
    
    unsigned char ciphertext[128];
    int len;
    EVP_EncryptUpdate(ctx, ciphertext, &len, 
        reinterpret_cast<const unsigned char*>(plaintext.c_str()), plaintext.size());
    
    int ciphertext_len = len;
    EVP_EncryptFinal_ex(ctx, ciphertext + len, &len);
    ciphertext_len += len;
    
    EVP_CIPHER_CTX_free(ctx);
    
    std::cout << "Encrypted with hardcoded key: ";
    for (int i = 0; i < ciphertext_len; i++)
        printf("%02x", ciphertext[i]);
    std::cout << std::endl;
}

// ============================================================================
// CATEGORY 6: CERTIFICATE VULNERABILITIES
// ============================================================================

/**
 * Vulnerability: Self-signed certificate with weak RSA
 */
void generateWeakSelfSignedCert() {
    RSA *rsa = RSA_new();
    BIGNUM *e = BN_new();
    BN_set_word(e, RSA_F4);
    
    // Vulnerability: Weak RSA key for certificate
    RSA_generate_key_ex(rsa, 1024, e, NULL);
    
    std::cout << "Weak self-signed certificate generated with RSA-1024" << std::endl;
    
    BN_free(e);
    RSA_free(rsa);
}

// ============================================================================
// CATEGORY 7: MULTIPLE COMBINED VULNERABILITIES
// ============================================================================

/**
 * Multiple vulnerabilities combined:
 * - Weak random number generation
 * - Insufficient key length
 * - Weak algorithm (DES)
 * - ECB mode
 */
void multipleVulnerabilities(const std::string& plaintext) {
    // Vulnerability 1: Weak random
    srand(123);
    unsigned char key[8];
    for (int i = 0; i < 8; i++) {
        key[i] = rand() % 256;
    }
    
    // Vulnerability 2 & 3: Weak algorithm (DES) + ECB mode
    DES_key_schedule schedule;
    DES_set_key_unchecked((const_DES_cblock*)key, &schedule);
    
    unsigned char input[8] = {0};
    unsigned char output[8] = {0};
    strncpy((char*)input, plaintext.c_str(), 8);
    
    DES_ecb_encrypt((const_DES_cblock*)input, (DES_cblock*)output, &schedule, DES_ENCRYPT);
    
    std::cout << "Multiple vulnerabilities: ";
    for (int i = 0; i < 8; i++)
        printf("%02x", output[i]);
    std::cout << std::endl;
}

// ============================================================================
// MAIN DEMONSTRATION
// ============================================================================

int main() {
    std::cout << "======================================================================" << std::endl;
    std::cout << "OPENSSL CRYPTO VULNERABILITIES - IBM Quantum Safe Explorer" << std::endl;
    std::cout << "======================================================================" << std::endl;
    
    std::string testData = "Sensitive Information";
    std::string testPassword = "password123";
    
    std::cout << "\n[1] WEAK HASH ALGORITHMS:" << std::endl;
    weakHashMD5(testData);
    weakHashSHA1(testData);
    weakPasswordHashMD5(testPassword);
    
    std::cout << "\n[2] WEAK SYMMETRIC ENCRYPTION:" << std::endl;
    encryptWithDES(testData);
    encryptWith3DES(testData);
    encryptWithRC4(testData);
    encryptWithAESECB(testData);
    encryptWithStaticIV(testData);
    
    std::cout << "\n[3] QUANTUM-VULNERABLE ASYMMETRIC CRYPTO:" << std::endl;
    generateRSA512();
    generateRSA1024();
    generateRSA2048();
    generateDSA1024();
    generateECDSAP256();
    generateECDSAP384();
    
    std::cout << "\n[4] INSECURE RANDOM NUMBER GENERATION:" << std::endl;
    insecureRandomCRand();
    insecureRandomPredictableSeed();
    insecureKeyGeneration();
    
    std::cout << "\n[5] HARDCODED SECRETS:" << std::endl;
    std::cout << "   Hardcoded key: " << HARDCODED_KEY << std::endl;
    encryptWithHardcodedKey(testData);
    
    std::cout << "\n[6] CERTIFICATE VULNERABILITIES:" << std::endl;
    generateWeakSelfSignedCert();
    
    std::cout << "\n[7] COMBINED VULNERABILITIES:" << std::endl;
    multipleVulnerabilities(testData);
    
    std::cout << "\n======================================================================" << std::endl;
    std::cout << "All OpenSSL vulnerability tests completed!" << std::endl;
    std::cout << "This file should trigger multiple findings in Quantum Safe Explorer!" << std::endl;
    std::cout << "======================================================================" << std::endl;
    
    return 0;
}

// Made with Bob