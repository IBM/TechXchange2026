import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.SecretKeyFactory;

import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.RSAKeyGenParameterSpec;
import java.util.Random;
import java.util.Base64;

/**
 * Comprehensive test file for Quantum Safe Explorer vulnerability detection.
 * Contains multiple categories of cryptographic vulnerabilities.
 * 
 * WARNING: This code is intentionally insecure for testing purposes only!
 * DO NOT use any of these patterns in production code.
 */
public class WeakCryptoVulnerabilities {
    
    // ============================================================================
    // CATEGORY 1: WEAK ALGORITHMS
    // ============================================================================
    
    /**
     * Vulnerability: MD5 hash algorithm (broken, collision attacks possible)
     */
    public String weakHashMD5(String data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] hash = md.digest(data.getBytes());
        return Base64.getEncoder().encodeToString(hash);
    }
    
    /**
     * Vulnerability: SHA-1 hash algorithm (deprecated, collision attacks demonstrated)
     */
    public String weakHashSHA1(String data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA1");
        byte[] hash = md.digest(data.getBytes());
        return Base64.getEncoder().encodeToString(hash);
    }
    
    /**
     * Vulnerability: DES encryption (56-bit key, easily brute-forced)
     */
    public byte[] weakEncryptionDES(String plaintext, byte[] key) throws Exception {
        SecretKeySpec keySpec = new SecretKeySpec(key, "DES");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: RC2 encryption (weak block cipher)
     */
    public byte[] weakEncryptionRC2(String plaintext, byte[] key) throws Exception {
        SecretKeySpec keySpec = new SecretKeySpec(key, "RC2");
        Cipher cipher = Cipher.getInstance("RC2/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: RC4 stream cipher (biased, multiple attacks)
     */
    public byte[] weakEncryptionRC4(String plaintext, byte[] key) throws Exception {
        SecretKeySpec keySpec = new SecretKeySpec(key, "ARCFOUR");
        Cipher cipher = Cipher.getInstance("ARCFOUR");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: Blowfish with weak key
     */
    public byte[] weakEncryptionBlowfish(String plaintext) throws Exception {
        KeyGenerator keyGen = KeyGenerator.getInstance("Blowfish");
        keyGen.init(64); // Very weak 64-bit key
        SecretKey key = keyGen.generateKey();
        
        Cipher cipher = Cipher.getInstance("Blowfish");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // ============================================================================
    // CATEGORY 2: INSUFFICIENT KEY LENGTHS
    // ============================================================================
    
    /**
     * Vulnerability: RSA with 512-bit key (extremely weak)
     */
    public KeyPair insufficientKeyRSA512() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
        keyGen.initialize(512); // Critically weak
        return keyGen.generateKeyPair();
    }
    
    /**
     * Vulnerability: RSA with 1024-bit key (insufficient for modern security)
     */
    public KeyPair insufficientKeyRSA1024() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
        keyGen.initialize(1024); // Weak, quantum-vulnerable
        return keyGen.generateKeyPair();
    }
    
    /**
     * Vulnerability: AES with 128-bit key (minimum, not recommended)
     */
    public SecretKey insufficientKeyAES128() throws Exception {
        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        keyGen.init(128); // Minimum key size
        return keyGen.generateKey();
    }
    
    /**
     * Vulnerability: DSA with 1024-bit key
     */
    public KeyPair insufficientKeyDSA1024() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("DSA");
        keyGen.initialize(1024); // Insufficient
        return keyGen.generateKeyPair();
    }
    
    /**
     * Vulnerability: Elliptic Curve with small key size
     */
    public KeyPair insufficientKeyEC160() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("EC");
        keyGen.initialize(160); // Too small
        return keyGen.generateKeyPair();
    }
    
    /**
     * Vulnerability: DH (Diffie-Hellman) with 1024-bit key
     */
    public KeyPair insufficientKeyDH1024() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("DH");
        keyGen.initialize(1024); // Insufficient
        return keyGen.generateKeyPair();
    }
    
    // ============================================================================
    // CATEGORY 3: DEPRECATED OR INSECURE CRYPTOGRAPHIC PRIMITIVES
    // ============================================================================
    
    /**
     * Vulnerability: ECB mode (Electronic Codebook) - patterns visible
     */
    public byte[] insecureModeECB(String plaintext, SecretKey key) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: No padding specified (defaults to insecure)
     */
    public byte[] insecureNoPadding(String plaintext, SecretKey key) throws Exception {
        Cipher cipher = Cipher.getInstance("AES");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: PKCS1Padding (vulnerable to padding oracle attacks)
     */
    public byte[] insecurePaddingPKCS1(String plaintext, KeyPair keyPair) throws Exception {
        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keyPair.getPublic());
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: PBE with MD5 and DES (weak password-based encryption)
     */
    public byte[] insecurePBEMD5DES(String plaintext, char[] password) throws Exception {
        PBEKeySpec keySpec = new PBEKeySpec(password);
        SecretKeyFactory keyFactory = SecretKeyFactory.getInstance("PBEWithMD5AndDES");
        SecretKey key = keyFactory.generateSecret(keySpec);
        
        Cipher cipher = Cipher.getInstance("PBEWithMD5AndDES");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: PBE with SHA1 and DES
     */
    public byte[] insecurePBESHA1DES(String plaintext, char[] password) throws Exception {
        PBEKeySpec keySpec = new PBEKeySpec(password);
        SecretKeyFactory keyFactory = SecretKeyFactory.getInstance("PBEWithSHA1AndDESede");
        SecretKey key = keyFactory.generateSecret(keySpec);
        
        Cipher cipher = Cipher.getInstance("PBEWithSHA1AndDESede");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Vulnerability: Static/hardcoded IV (Initialization Vector)
     */
    public byte[] insecureStaticIV(String plaintext, SecretKey key) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        // Hardcoded IV - major security flaw
        byte[] staticIV = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                          0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F};
        IvParameterSpec ivSpec = new IvParameterSpec(staticIV);
        cipher.init(Cipher.ENCRYPT_MODE, key, ivSpec);
        return cipher.doFinal(plaintext.getBytes());
    }

    /**
     * Null cipher (no encryption). Returns plaintext bytes unchanged.
     */
    public byte[] insecureNullCipher(String plaintext) {
        return plaintext.getBytes(StandardCharsets.UTF_8);
    }
    
    // ============================================================================
    // CATEGORY 4: UNSAFE RANDOM NUMBER USAGE
    // ============================================================================
    
    /**
     * Vulnerability: Using java.util.Random for cryptographic purposes
     */
    public byte[] unsafeRandomJavaUtil() {
        Random random = new Random(); // NOT cryptographically secure
        byte[] randomBytes = new byte[16];
        random.nextBytes(randomBytes);
        return randomBytes;
    }
    
    /**
     * Vulnerability: Using java.util.Random with predictable seed
     */
    public byte[] unsafeRandomPredictableSeed() {
        Random random = new Random(12345L); // Fixed seed - completely predictable
        byte[] randomBytes = new byte[16];
        random.nextBytes(randomBytes);
        return randomBytes;
    }
    
    /**
     * Vulnerability: Using Math.random() for security
     */
    public double unsafeRandomMath() {
        return Math.random(); // NOT cryptographically secure
    }
    
    /**
     * Vulnerability: Weak random for key generation
     */
    public byte[] unsafeRandomKeyGeneration() {
        Random random = new Random(System.currentTimeMillis()); // Predictable
        byte[] key = new byte[32];
        random.nextBytes(key);
        return key;
    }
    
    /**
     * Vulnerability: SecureRandom with weak algorithm
     */
    public byte[] unsafeRandomWeakAlgorithm() throws Exception {
        SecureRandom random = SecureRandom.getInstance("SHA1PRNG"); // Weak
        byte[] randomBytes = new byte[16];
        random.nextBytes(randomBytes);
        return randomBytes;
    }
    
    /**
     * Vulnerability: Reusing SecureRandom without reseeding
     */
    private static SecureRandom sharedRandom = new SecureRandom(); // Shared instance
    public byte[] unsafeRandomSharedInstance() {
        byte[] randomBytes = new byte[16];
        sharedRandom.nextBytes(randomBytes); // Reusing without reseed
        return randomBytes;
    }
    
    /**
     * Vulnerability: Using timestamp as seed
     */
    public byte[] unsafeRandomTimestampSeed() {
        Random random = new Random(System.nanoTime()); // Predictable
        byte[] randomBytes = new byte[16];
        random.nextBytes(randomBytes);
        return randomBytes;
    }
    
    // ============================================================================
    // COMBINED VULNERABILITIES
    // ============================================================================
    
    /**
     * Multiple vulnerabilities: Weak algorithm + insufficient key + unsafe random
     */
    public byte[] multipleVulnerabilities(String plaintext) throws Exception {
        // Unsafe random
        Random random = new Random();
        byte[] key = new byte[8]; // Insufficient key length
        random.nextBytes(key);
        
        // Weak algorithm (DES)
        SecretKeySpec keySpec = new SecretKeySpec(key, "DES");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding"); // ECB mode
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    /**
     * Hardcoded cryptographic key (critical vulnerability)
     */
    public byte[] hardcodedKey(String plaintext) throws Exception {
        // Hardcoded key - never do this!
        byte[] hardcodedKeyBytes = "MySecretKey12345".getBytes();
        SecretKeySpec keySpec = new SecretKeySpec(hardcodedKeyBytes, "AES");
        Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // ============================================================================
    // MAIN METHOD FOR TESTING
    // ============================================================================
    
    public static void main(String[] args) {
        WeakCryptoVulnerabilities vuln = new WeakCryptoVulnerabilities();
        
        try {
            System.out.println("=== Testing Cryptographic Vulnerabilities ===\n");
            
            String testData = "Sensitive Information";
            
            // Test weak algorithms
            System.out.println("1. WEAK ALGORITHMS:");
            System.out.println("   MD5 Hash: " + vuln.weakHashMD5(testData));
            System.out.println("   SHA-1 Hash: " + vuln.weakHashSHA1(testData));
            
            // Test insufficient key lengths
            System.out.println("\n2. INSUFFICIENT KEY LENGTHS:");
            KeyPair rsa512 = vuln.insufficientKeyRSA512();
            System.out.println("   RSA-512 KeyPair generated");
            KeyPair rsa1024 = vuln.insufficientKeyRSA1024();
            System.out.println("   RSA-1024 KeyPair generated");
            
            // Test deprecated primitives
            System.out.println("\n3. DEPRECATED/INSECURE PRIMITIVES:");
            SecretKey aesKey = vuln.insufficientKeyAES128();
            byte[] ecbEncrypted = vuln.insecureModeECB(testData, aesKey);
            System.out.println("   ECB Mode encryption completed");
            
            // Test unsafe random
            System.out.println("\n4. UNSAFE RANDOM NUMBER USAGE:");
            byte[] unsafeRandom = vuln.unsafeRandomJavaUtil();
            System.out.println("   Unsafe random bytes generated: " + 
                             Base64.getEncoder().encodeToString(unsafeRandom));
            
            // Test combined vulnerabilities
            System.out.println("\n5. COMBINED VULNERABILITIES:");
            byte[] multiVuln = vuln.multipleVulnerabilities(testData);
            System.out.println("   Multiple vulnerabilities test completed");
            
            System.out.println("\n=== All vulnerability tests completed ===");
            System.out.println("This file should trigger multiple findings in Quantum Safe Explorer!");
            
        } catch (Exception e) {
            System.err.println("Error during testing: " + e.getMessage());
            e.printStackTrace();
        }
    }
}

// Made with Bob
