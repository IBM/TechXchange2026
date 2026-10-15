import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import javax.crypto.spec.IvParameterSpec;
import java.security.MessageDigest;
import java.security.KeyPairGenerator;
import java.security.KeyPair;
import java.security.Signature;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * Sample Java file with cryptographic vulnerabilities for testing Quantum Safe Explorer.
 * This file contains multiple quantum-vulnerable cryptographic implementations.
 * 
 * WARNING: This code is intentionally insecure and should NOT be used in production!
 */
public class VulnerableCryptoExample {
    
    // Vulnerable: Using weak MD5 hash algorithm
    public String hashPasswordMD5(String password) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] hash = md.digest(password.getBytes());
        return Base64.getEncoder().encodeToString(hash);
    }
    
    // Vulnerable: Using SHA-1 which is deprecated
    public String hashDataSHA1(String data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        byte[] hash = md.digest(data.getBytes());
        return Base64.getEncoder().encodeToString(hash);
    }
    
    // Vulnerable: Using DES encryption (weak key size)
    public byte[] encryptWithDES(String plaintext, String key) throws Exception {
        SecretKeySpec secretKey = new SecretKeySpec(key.getBytes(), "DES");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, secretKey);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using 3DES (Triple DES) - quantum vulnerable
    public byte[] encryptWith3DES(String plaintext, byte[] keyBytes) throws Exception {
        SecretKeySpec secretKey = new SecretKeySpec(keyBytes, "DESede");
        Cipher cipher = Cipher.getInstance("DESede/CBC/PKCS5Padding");
        byte[] iv = new byte[8];
        new SecureRandom().nextBytes(iv);
        IvParameterSpec ivSpec = new IvParameterSpec(iv);
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, ivSpec);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using AES with small key size (128-bit)
    public byte[] encryptWithAES128(String plaintext) throws Exception {
        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        keyGen.init(128); // Vulnerable: 128-bit key
        SecretKey secretKey = keyGen.generateKey();
        
        Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, secretKey);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using RSA with small key size (1024-bit)
    public KeyPair generateRSA1024KeyPair() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
        keyGen.initialize(1024); // Vulnerable: 1024-bit RSA
        return keyGen.generateKeyPair();
    }
    
    // Vulnerable: Using RSA with 2048-bit (quantum vulnerable)
    public KeyPair generateRSA2048KeyPair() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
        keyGen.initialize(2048); // Quantum vulnerable
        return keyGen.generateKeyPair();
    }
    
    // Vulnerable: Using DSA (Digital Signature Algorithm)
    public byte[] signWithDSA(byte[] data, KeyPair keyPair) throws Exception {
        Signature signature = Signature.getInstance("SHA256withDSA");
        signature.initSign(keyPair.getPrivate());
        signature.update(data);
        return signature.sign();
    }
    
    // Vulnerable: Using ECDSA (Elliptic Curve Digital Signature Algorithm)
    public KeyPair generateECDSAKeyPair() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("EC");
        keyGen.initialize(256); // Quantum vulnerable
        return keyGen.generateKeyPair();
    }
    
    // Vulnerable: Using ECDSA for signing
    public byte[] signWithECDSA(byte[] data, KeyPair keyPair) throws Exception {
        Signature signature = Signature.getInstance("SHA256withECDSA");
        signature.initSign(keyPair.getPrivate());
        signature.update(data);
        return signature.sign();
    }
    
    // Vulnerable: Using Diffie-Hellman key exchange
    public KeyPair generateDHKeyPair() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("DH");
        keyGen.initialize(2048); // Quantum vulnerable
        return keyGen.generateKeyPair();
    }
    
    // Vulnerable: Using RC4 stream cipher
    public byte[] encryptWithRC4(String plaintext, byte[] key) throws Exception {
        SecretKeySpec secretKey = new SecretKeySpec(key, "RC4");
        Cipher cipher = Cipher.getInstance("RC4");
        cipher.init(Cipher.ENCRYPT_MODE, secretKey);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using Blowfish with small key
    public byte[] encryptWithBlowfish(String plaintext) throws Exception {
        KeyGenerator keyGen = KeyGenerator.getInstance("Blowfish");
        keyGen.init(128);
        SecretKey secretKey = keyGen.generateKey();
        
        Cipher cipher = Cipher.getInstance("Blowfish/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, secretKey);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using RSA with PKCS1 padding (vulnerable to padding oracle attacks)
    public byte[] encryptWithRSAPKCS1(String plaintext, KeyPair keyPair) throws Exception {
        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keyPair.getPublic());
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using ECB mode (Electronic Codebook) - not quantum-specific but insecure
    public byte[] encryptWithAESECB(String plaintext, SecretKey key) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using static/hardcoded IV
    public byte[] encryptWithStaticIV(String plaintext, SecretKey key) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        byte[] staticIV = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}; // Bad practice
        IvParameterSpec ivSpec = new IvParameterSpec(staticIV);
        cipher.init(Cipher.ENCRYPT_MODE, key, ivSpec);
        return cipher.doFinal(plaintext.getBytes());
    }
    
    // Vulnerable: Using SHA-256 with RSA signature (quantum vulnerable)
    public byte[] signWithRSASHA256(byte[] data, KeyPair keyPair) throws Exception {
        Signature signature = Signature.getInstance("SHA256withRSA");
        signature.initSign(keyPair.getPrivate());
        signature.update(data);
        return signature.sign();
    }
    
    // Main method demonstrating usage
    public static void main(String[] args) {
        VulnerableCryptoExample example = new VulnerableCryptoExample();
        
        try {
            // Test various vulnerable cryptographic operations
            System.out.println("Testing vulnerable cryptographic implementations...");
            
            String testData = "Sensitive data to encrypt";
            
            // MD5 hashing
            String md5Hash = example.hashPasswordMD5("password123");
            System.out.println("MD5 Hash: " + md5Hash);
            
            // SHA-1 hashing
            String sha1Hash = example.hashDataSHA1(testData);
            System.out.println("SHA-1 Hash: " + sha1Hash);
            
            // RSA key generation
            KeyPair rsaKeyPair = example.generateRSA2048KeyPair();
            System.out.println("RSA KeyPair generated");
            
            // ECDSA key generation
            KeyPair ecdsaKeyPair = example.generateECDSAKeyPair();
            System.out.println("ECDSA KeyPair generated");
            
            // AES encryption
            byte[] encrypted = example.encryptWithAES128(testData);
            System.out.println("AES Encrypted: " + Base64.getEncoder().encodeToString(encrypted));
            
            System.out.println("\nAll vulnerable operations completed successfully.");
            System.out.println("This code should be detected by Quantum Safe Explorer!");
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}

// Made with Bob
