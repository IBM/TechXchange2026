using System;
using System.IO;
using System.Text;
using System.Security.Cryptography;

/*
 * Comprehensive C# (.NET) cryptographic vulnerabilities for testing IBM Quantum Safe Explorer.
 * This file contains multiple quantum-vulnerable and weak cryptographic implementations.
 * 
 * WARNING: This code is intentionally insecure and should NOT be used in production!
 */

namespace VulnerableCryptoExamples
{
    public class VulnerableCrypto
    {
        // ============================================================================
        // CATEGORY 1: WEAK HASH ALGORITHMS
        // ============================================================================

        /// <summary>
        /// Vulnerability: MD5 hash algorithm (broken, collision attacks)
        /// </summary>
        public static string WeakHashMD5(string data)
        {
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(data));
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        /// <summary>
        /// Vulnerability: SHA-1 hash algorithm (deprecated, collision attacks)
        /// </summary>
        public static string WeakHashSHA1(string data)
        {
            using (SHA1 sha1 = SHA1.Create())
            {
                byte[] hash = sha1.ComputeHash(Encoding.UTF8.GetBytes(data));
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        /// <summary>
        /// Vulnerability: Using MD5 for password hashing
        /// </summary>
        public static string WeakPasswordHashMD5(string password)
        {
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(password));
                return Convert.ToBase64String(hash);
            }
        }

        /// <summary>
        /// Vulnerability: Using SHA-1 for password hashing
        /// </summary>
        public static string WeakPasswordHashSHA1(string password)
        {
            using (SHA1 sha1 = SHA1.Create())
            {
                byte[] hash = sha1.ComputeHash(Encoding.UTF8.GetBytes(password));
                return Convert.ToBase64String(hash);
            }
        }

        // ============================================================================
        // CATEGORY 2: WEAK SYMMETRIC ENCRYPTION
        // ============================================================================

        /// <summary>
        /// Vulnerability: DES encryption (56-bit key, easily brute-forced)
        /// </summary>
        public static string EncryptWithDES(string plaintext, byte[] key)
        {
            using (DES des = DES.Create())
            {
                des.Key = key;
                des.Mode = CipherMode.ECB; // Vulnerability: ECB mode
                des.Padding = PaddingMode.PKCS7;

                using (ICryptoTransform encryptor = des.CreateEncryptor())
                {
                    byte[] plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
                    byte[] ciphertext = encryptor.TransformFinalBlock(plaintextBytes, 0, plaintextBytes.Length);
                    return Convert.ToBase64String(ciphertext);
                }
            }
        }

        /// <summary>
        /// Vulnerability: 3DES/Triple DES (quantum vulnerable, deprecated)
        /// </summary>
        public static string EncryptWithTripleDES(string plaintext, byte[] key)
        {
            using (TripleDES tripleDes = TripleDES.Create())
            {
                tripleDes.Key = key;
                tripleDes.Mode = CipherMode.ECB; // Vulnerability: ECB mode
                tripleDes.Padding = PaddingMode.PKCS7;

                using (ICryptoTransform encryptor = tripleDes.CreateEncryptor())
                {
                    byte[] plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
                    byte[] ciphertext = encryptor.TransformFinalBlock(plaintextBytes, 0, plaintextBytes.Length);
                    return Convert.ToBase64String(ciphertext);
                }
            }
        }

        /// <summary>
        /// Vulnerability: RC2 encryption (weak block cipher)
        /// </summary>
        public static string EncryptWithRC2(string plaintext, byte[] key)
        {
            using (RC2 rc2 = RC2.Create())
            {
                rc2.Key = key;
                rc2.Mode = CipherMode.ECB;
                rc2.Padding = PaddingMode.PKCS7;

                using (ICryptoTransform encryptor = rc2.CreateEncryptor())
                {
                    byte[] plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
                    byte[] ciphertext = encryptor.TransformFinalBlock(plaintextBytes, 0, plaintextBytes.Length);
                    return Convert.ToBase64String(ciphertext);
                }
            }
        }

        /// <summary>
        /// Vulnerability: AES with ECB mode (pattern leakage)
        /// </summary>
        public static string EncryptWithAESECB(string plaintext, byte[] key)
        {
            using (Aes aes = Aes.Create())
            {
                aes.Key = key;
                aes.Mode = CipherMode.ECB; // Vulnerability: ECB mode
                aes.Padding = PaddingMode.PKCS7;

                using (ICryptoTransform encryptor = aes.CreateEncryptor())
                {
                    byte[] plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
                    byte[] ciphertext = encryptor.TransformFinalBlock(plaintextBytes, 0, plaintextBytes.Length);
                    return Convert.ToBase64String(ciphertext);
                }
            }
        }

        /// <summary>
        /// Vulnerability: Using static/hardcoded IV
        /// </summary>
        public static string EncryptWithStaticIV(string plaintext, byte[] key)
        {
            using (Aes aes = Aes.Create())
            {
                aes.Key = key;
                aes.Mode = CipherMode.CBC;
                // Vulnerability: Hardcoded IV - major security flaw
                aes.IV = new byte[16]; // All zeros
                aes.Padding = PaddingMode.PKCS7;

                using (ICryptoTransform encryptor = aes.CreateEncryptor())
                {
                    byte[] plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
                    byte[] ciphertext = encryptor.TransformFinalBlock(plaintextBytes, 0, plaintextBytes.Length);
                    return Convert.ToBase64String(ciphertext);
                }
            }
        }

        // ============================================================================
        // CATEGORY 3: WEAK ASYMMETRIC CRYPTOGRAPHY (QUANTUM VULNERABLE)
        // ============================================================================

        /// <summary>
        /// Vulnerability: RSA with 512-bit key (extremely weak)
        /// </summary>
        public static RSACryptoServiceProvider GenerateRSA512()
        {
            RSACryptoServiceProvider rsa = new RSACryptoServiceProvider(512);
            return rsa;
        }

        /// <summary>
        /// Vulnerability: RSA with 1024-bit key (insufficient, quantum vulnerable)
        /// </summary>
        public static RSACryptoServiceProvider GenerateRSA1024()
        {
            RSACryptoServiceProvider rsa = new RSACryptoServiceProvider(1024);
            return rsa;
        }

        /// <summary>
        /// Vulnerability: RSA with 2048-bit key (quantum vulnerable)
        /// </summary>
        public static RSACryptoServiceProvider GenerateRSA2048()
        {
            RSACryptoServiceProvider rsa = new RSACryptoServiceProvider(2048);
            return rsa;
        }

        /// <summary>
        /// Vulnerability: RSA signature (quantum vulnerable)
        /// </summary>
        public static string SignWithRSA(string message, RSACryptoServiceProvider rsa)
        {
            byte[] messageBytes = Encoding.UTF8.GetBytes(message);
            byte[] signature = rsa.SignData(messageBytes, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
            return Convert.ToBase64String(signature);
        }

        /// <summary>
        /// Vulnerability: DSA key generation (quantum vulnerable)
        /// </summary>
        public static DSACryptoServiceProvider GenerateDSA1024()
        {
            DSACryptoServiceProvider dsa = new DSACryptoServiceProvider(1024);
            return dsa;
        }

        /// <summary>
        /// Vulnerability: DSA signature (quantum vulnerable)
        /// </summary>
        public static string SignWithDSA(string message, DSACryptoServiceProvider dsa)
        {
            byte[] messageBytes = Encoding.UTF8.GetBytes(message);
            byte[] signature = dsa.SignData(messageBytes);
            return Convert.ToBase64String(signature);
        }

        /// <summary>
        /// Vulnerability: ECDSA P-256 curve (quantum vulnerable)
        /// </summary>
        public static ECDsaCng GenerateECDSAP256()
        {
            ECDsaCng ecdsa = new ECDsaCng(256);
            return ecdsa;
        }

        /// <summary>
        /// Vulnerability: ECDSA signature (quantum vulnerable)
        /// </summary>
        public static string SignWithECDSA(string message, ECDsaCng ecdsa)
        {
            byte[] messageBytes = Encoding.UTF8.GetBytes(message);
            byte[] signature = ecdsa.SignData(messageBytes);
            return Convert.ToBase64String(signature);
        }

        // ============================================================================
        // CATEGORY 4: INSECURE RANDOM NUMBER GENERATION
        // ============================================================================

        /// <summary>
        /// Vulnerability: Using System.Random for cryptographic purposes
        /// </summary>
        public static int InsecureRandomSystemRandom()
        {
            Random random = new Random();
            return random.Next(0, 1000000);
        }

        /// <summary>
        /// Vulnerability: Using predictable seed
        /// </summary>
        public static int InsecureRandomWithSeed()
        {
            Random random = new Random(12345); // Fixed seed - completely predictable
            return random.Next(0, 1000000);
        }

        /// <summary>
        /// Vulnerability: Using time as seed (predictable)
        /// </summary>
        public static int InsecureRandomTimeSeed()
        {
            Random random = new Random((int)DateTime.Now.Ticks);
            return random.Next(0, 1000000);
        }

        /// <summary>
        /// Vulnerability: Generating cryptographic key with weak random
        /// </summary>
        public static byte[] InsecureKeyGeneration()
        {
            Random random = new Random(42);
            byte[] key = new byte[16];
            random.NextBytes(key);
            return key;
        }

        // ============================================================================
        // CATEGORY 5: HARDCODED SECRETS
        // ============================================================================

        // Vulnerability: Hardcoded encryption key
        private static readonly byte[] HardcodedKey = Encoding.UTF8.GetBytes("SuperSecretKey16");

        // Vulnerability: Hardcoded IV
        private static readonly byte[] HardcodedIV = Encoding.UTF8.GetBytes("InitVector123456");

        // Vulnerability: Hardcoded password
        private const string HardcodedPassword = "admin123";

        /// <summary>
        /// Vulnerability: Using hardcoded key for encryption
        /// </summary>
        public static string EncryptWithHardcodedKey(string plaintext)
        {
            using (Aes aes = Aes.Create())
            {
                aes.Key = HardcodedKey;
                aes.IV = HardcodedIV;
                aes.Mode = CipherMode.CBC;
                aes.Padding = PaddingMode.PKCS7;

                using (ICryptoTransform encryptor = aes.CreateEncryptor())
                {
                    byte[] plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
                    byte[] ciphertext = encryptor.TransformFinalBlock(plaintextBytes, 0, plaintextBytes.Length);
                    return Convert.ToBase64String(ciphertext);
                }
            }
        }

        // ============================================================================
        // CATEGORY 6: INSUFFICIENT KEY LENGTHS
        // ============================================================================

        /// <summary>
        /// Vulnerability: AES with 128-bit key (minimum, not recommended for quantum safety)
        /// </summary>
        public static byte[] GenerateAES128Key()
        {
            using (Aes aes = Aes.Create())
            {
                aes.KeySize = 128;
                aes.GenerateKey();
                return aes.Key;
            }
        }

        /// <summary>
        /// Vulnerability: DES key (only 56 effective bits)
        /// </summary>
        public static byte[] GenerateWeakDESKey()
        {
            using (DES des = DES.Create())
            {
                des.GenerateKey();
                return des.Key;
            }
        }

        // ============================================================================
        // CATEGORY 7: HMAC WITH WEAK ALGORITHMS
        // ============================================================================

        /// <summary>
        /// Vulnerability: HMAC with MD5
        /// </summary>
        public static string HMACWithMD5(string data, byte[] key)
        {
            using (HMACMD5 hmac = new HMACMD5(key))
            {
                byte[] hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(data));
                return Convert.ToBase64String(hash);
            }
        }

        /// <summary>
        /// Vulnerability: HMAC with SHA-1
        /// </summary>
        public static string HMACWithSHA1(string data, byte[] key)
        {
            using (HMACSHA1 hmac = new HMACSHA1(key))
            {
                byte[] hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(data));
                return Convert.ToBase64String(hash);
            }
        }

        // ============================================================================
        // CATEGORY 8: MULTIPLE COMBINED VULNERABILITIES
        // ============================================================================

        /// <summary>
        /// Multiple vulnerabilities combined:
        /// - Weak random number generation
        /// - Insufficient key length
        /// - Weak algorithm (DES)
        /// - ECB mode
        /// </summary>
        public static string MultipleVulnerabilities(string plaintext)
        {
            // Vulnerability 1: Weak random
            Random random = new Random(123);
            byte[] key = new byte[8];
            random.NextBytes(key);

            // Vulnerability 2 & 3: Weak algorithm (DES) + ECB mode
            using (DES des = DES.Create())
            {
                des.Key = key;
                des.Mode = CipherMode.ECB;
                des.Padding = PaddingMode.PKCS7;

                using (ICryptoTransform encryptor = des.CreateEncryptor())
                {
                    byte[] plaintextBytes = Encoding.UTF8.GetBytes(plaintext);
                    byte[] ciphertext = encryptor.TransformFinalBlock(plaintextBytes, 0, plaintextBytes.Length);
                    return Convert.ToBase64String(ciphertext);
                }
            }
        }

        // ============================================================================
        // MAIN DEMONSTRATION
        // ============================================================================

        public static void Main(string[] args)
        {
            Console.WriteLine("======================================================================");
            Console.WriteLine("CRYPTOGRAPHIC VULNERABILITIES TEST - IBM Quantum Safe Explorer");
            Console.WriteLine("======================================================================");

            string testData = "Sensitive Information";
            string testPassword = "password123";

            Console.WriteLine("\n[1] WEAK HASH ALGORITHMS:");
            Console.WriteLine($"   MD5 Hash: {WeakHashMD5(testData)}");
            Console.WriteLine($"   SHA-1 Hash: {WeakHashSHA1(testData)}");
            Console.WriteLine($"   MD5 Password Hash: {WeakPasswordHashMD5(testPassword)}");

            Console.WriteLine("\n[2] WEAK SYMMETRIC ENCRYPTION:");
            byte[] desKey = Encoding.UTF8.GetBytes("8bytekey");
            Console.WriteLine($"   DES Encrypted: {EncryptWithDES(testData, desKey)}");

            byte[] tripleDesKey = Encoding.UTF8.GetBytes("24ByteKeyForTripleDES123");
            Console.WriteLine($"   3DES Encrypted: {EncryptWithTripleDES(testData, tripleDesKey)}");

            byte[] aesKey = new byte[16];
            Console.WriteLine($"   AES-ECB Encrypted: {EncryptWithAESECB(testData, aesKey)}");

            Console.WriteLine("\n[3] QUANTUM-VULNERABLE ASYMMETRIC CRYPTO:");
            using (RSACryptoServiceProvider rsa512 = GenerateRSA512())
            {
                Console.WriteLine($"   RSA-512 key generated: {rsa512.KeySize} bits");
            }

            using (RSACryptoServiceProvider rsa1024 = GenerateRSA1024())
            {
                Console.WriteLine($"   RSA-1024 key generated: {rsa1024.KeySize} bits");
            }

            using (RSACryptoServiceProvider rsa2048 = GenerateRSA2048())
            {
                Console.WriteLine($"   RSA-2048 key generated: {rsa2048.KeySize} bits");
            }

            using (DSACryptoServiceProvider dsa = GenerateDSA1024())
            {
                Console.WriteLine($"   DSA-1024 key generated");
            }

            using (ECDsaCng ecdsa = GenerateECDSAP256())
            {
                Console.WriteLine($"   ECDSA P-256 key generated");
            }

            Console.WriteLine("\n[4] INSECURE RANDOM NUMBER GENERATION:");
            Console.WriteLine($"   Insecure random: {InsecureRandomSystemRandom()}");
            Console.WriteLine($"   Predictable seed random: {InsecureRandomWithSeed()}");
            Console.WriteLine($"   Time-based seed random: {InsecureRandomTimeSeed()}");

            Console.WriteLine("\n[5] HARDCODED SECRETS:");
            Console.WriteLine($"   Hardcoded key: {Encoding.UTF8.GetString(HardcodedKey)}");
            Console.WriteLine($"   Encrypted with hardcoded key: {EncryptWithHardcodedKey(testData)}");

            Console.WriteLine("\n[6] HMAC WITH WEAK ALGORITHMS:");
            byte[] hmacKey = Encoding.UTF8.GetBytes("hmackey");
            Console.WriteLine($"   HMAC-MD5: {HMACWithMD5(testData, hmacKey)}");
            Console.WriteLine($"   HMAC-SHA1: {HMACWithSHA1(testData, hmacKey)}");

            Console.WriteLine("\n[7] COMBINED VULNERABILITIES:");
            Console.WriteLine($"   Multiple vulnerabilities: {MultipleVulnerabilities(testData)}");

            Console.WriteLine("\n======================================================================");
            Console.WriteLine("All vulnerability tests completed!");
            Console.WriteLine("This file should trigger multiple findings in Quantum Safe Explorer!");
            Console.WriteLine("======================================================================");
        }
    }
}

// Made with Bob