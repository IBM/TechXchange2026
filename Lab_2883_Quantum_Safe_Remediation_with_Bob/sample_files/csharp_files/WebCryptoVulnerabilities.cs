using System;
using System.Text;
using System.Security.Cryptography;
using System.Web;
using System.IdentityModel.Tokens.Jwt;
using Microsoft.IdentityModel.Tokens;

/*
 * C# ASP.NET Web Cryptographic Vulnerabilities
 * Testing file for IBM Quantum Safe Explorer
 * 
 * WARNING: This code is intentionally insecure and should NOT be used in production!
 */

namespace WebCryptoVulnerabilities
{
    // ============================================================================
    // JWT VULNERABILITIES
    // ============================================================================

    public class InsecureJWTHandler
    {
        // Vulnerability: Weak secret key
        private const string WeakSecret = "weak_secret";

        /// <summary>
        /// Vulnerability: JWT with weak secret
        /// </summary>
        public string CreateJWTWeakSecret(int userId)
        {
            var tokenHandler = new JwtSecurityTokenHandler();
            var key = Encoding.ASCII.GetBytes(WeakSecret);
            var tokenDescriptor = new SecurityTokenDescriptor
            {
                Subject = new System.Security.Claims.ClaimsIdentity(new[]
                {
                    new System.Security.Claims.Claim("user_id", userId.ToString())
                }),
                Expires = DateTime.UtcNow.AddHours(24),
                SigningCredentials = new SigningCredentials(
                    new SymmetricSecurityKey(key),
                    SecurityAlgorithms.HmacSha256Signature)
            };
            var token = tokenHandler.CreateToken(tokenDescriptor);
            return tokenHandler.WriteToken(token);
        }

        /// <summary>
        /// Vulnerability: JWT without expiration
        /// </summary>
        public string CreateJWTNoExpiration(int userId)
        {
            var tokenHandler = new JwtSecurityTokenHandler();
            var key = Encoding.ASCII.GetBytes(WeakSecret);
            var tokenDescriptor = new SecurityTokenDescriptor
            {
                Subject = new System.Security.Claims.ClaimsIdentity(new[]
                {
                    new System.Security.Claims.Claim("user_id", userId.ToString())
                }),
                // Vulnerability: No expiration set
                SigningCredentials = new SigningCredentials(
                    new SymmetricSecurityKey(key),
                    SecurityAlgorithms.HmacSha256Signature)
            };
            var token = tokenHandler.CreateToken(tokenDescriptor);
            return tokenHandler.WriteToken(token);
        }

        /// <summary>
        /// Vulnerability: JWT with RSA (quantum vulnerable)
        /// </summary>
        public string CreateJWTRSAWeak(int userId)
        {
            using (RSACryptoServiceProvider rsa = new RSACryptoServiceProvider(1024))
            {
                var tokenHandler = new JwtSecurityTokenHandler();
                var tokenDescriptor = new SecurityTokenDescriptor
                {
                    Subject = new System.Security.Claims.ClaimsIdentity(new[]
                    {
                        new System.Security.Claims.Claim("user_id", userId.ToString())
                    }),
                    Expires = DateTime.UtcNow.AddHours(24),
                    SigningCredentials = new SigningCredentials(
                        new RsaSecurityKey(rsa),
                        SecurityAlgorithms.RsaSha256)
                };
                var token = tokenHandler.CreateToken(tokenDescriptor);
                return tokenHandler.WriteToken(token);
            }
        }
    }

    // ============================================================================
    // SESSION MANAGEMENT VULNERABILITIES
    // ============================================================================

    public class InsecureSessionManager
    {
        // Vulnerability: Hardcoded secret
        private const string SecretKey = "hardcoded-session-secret";

        /// <summary>
        /// Vulnerability: Weak session token generation
        /// </summary>
        public string CreateSessionTokenWeak(int userId)
        {
            Random random = new Random(userId); // Vulnerability: Predictable seed
            byte[] token = new byte[32];
            random.NextBytes(token);
            return Convert.ToBase64String(token);
        }

        /// <summary>
        /// Vulnerability: Using MD5 for HMAC
        /// </summary>
        public string SignSessionDataMD5(string data)
        {
            using (HMACMD5 hmac = new HMACMD5(Encoding.UTF8.GetBytes(SecretKey)))
            {
                byte[] hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(data));
                return Convert.ToBase64String(hash);
            }
        }

        /// <summary>
        /// Vulnerability: Using SHA-1 for HMAC
        /// </summary>
        public string SignSessionDataSHA1(string data)
        {
            using (HMACSHA1 hmac = new HMACSHA1(Encoding.UTF8.GetBytes(SecretKey)))
            {
                byte[] hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(data));
                return Convert.ToBase64String(hash);
            }
        }
    }

    // ============================================================================
    // API KEY GENERATION VULNERABILITIES
    // ============================================================================

    public class InsecureAPIKeyGenerator
    {
        /// <summary>
        /// Vulnerability: Using weak random for API keys
        /// </summary>
        public string GenerateAPIKeyWeakRandom()
        {
            Random random = new Random((int)DateTime.Now.Ticks); // Vulnerability: Predictable
            byte[] key = new byte[32];
            random.NextBytes(key);
            return Convert.ToBase64String(key);
        }

        /// <summary>
        /// Vulnerability: Predictable API key based on user ID
        /// </summary>
        public string GenerateAPIKeyPredictable(int userId)
        {
            string data = $"api_key_{userId}";
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(data));
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        /// <summary>
        /// Vulnerability: Sequential API keys
        /// </summary>
        public string GenerateAPIKeySequential(int counter)
        {
            return $"API-{counter:D8}";
        }
    }

    // ============================================================================
    // PASSWORD HASHING VULNERABILITIES
    // ============================================================================

    public class InsecurePasswordHasher
    {
        /// <summary>
        /// Vulnerability: MD5 for password hashing
        /// </summary>
        public string HashPasswordMD5(string password)
        {
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(password));
                return Convert.ToBase64String(hash);
            }
        }

        /// <summary>
        /// Vulnerability: SHA-1 for password hashing
        /// </summary>
        public string HashPasswordSHA1(string password)
        {
            using (SHA1 sha1 = SHA1.Create())
            {
                byte[] hash = sha1.ComputeHash(Encoding.UTF8.GetBytes(password));
                return Convert.ToBase64String(hash);
            }
        }

        /// <summary>
        /// Vulnerability: MD5 with weak salt
        /// </summary>
        public string HashPasswordMD5WithSalt(string password)
        {
            Random random = new Random((int)DateTime.Now.Ticks);
            string salt = random.Next(10000).ToString(); // Weak salt
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(salt + password));
                return $"{salt}:{Convert.ToBase64String(hash)}";
            }
        }

        /// <summary>
        /// Vulnerability: Timing attack in password verification
        /// </summary>
        public bool VerifyPasswordTimingAttack(string password, string hashed)
        {
            return HashPasswordMD5(password) == hashed; // Not constant-time
        }
    }

    // ============================================================================
    // PASSWORD RESET TOKEN VULNERABILITIES
    // ============================================================================

    public class InsecurePasswordResetHandler
    {
        /// <summary>
        /// Vulnerability: Predictable reset token
        /// </summary>
        public string GenerateResetTokenWeak(string email)
        {
            long timestamp = DateTime.Now.Ticks;
            string data = $"{email}{timestamp}";
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(data));
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        /// <summary>
        /// Vulnerability: Reset token without expiration
        /// </summary>
        public string GenerateResetTokenNoExpiry(int userId)
        {
            Random random = new Random(userId);
            StringBuilder token = new StringBuilder();
            for (int i = 0; i < 6; i++)
            {
                token.Append(random.Next(10));
            }
            return token.ToString();
        }

        /// <summary>
        /// Vulnerability: Timing attack in token verification
        /// </summary>
        public bool VerifyResetTokenTiming(string token, string expected)
        {
            return token == expected; // Not constant-time comparison
        }
    }

    // ============================================================================
    // TWO-FACTOR AUTHENTICATION VULNERABILITIES
    // ============================================================================

    public class Insecure2FAHandler
    {
        /// <summary>
        /// Vulnerability: Weak TOTP secret generation
        /// </summary>
        public string GenerateTOTPSecretWeak()
        {
            Random random = new Random(42); // Vulnerability: Fixed seed
            byte[] secret = new byte[10];
            random.NextBytes(secret);
            return Convert.ToBase64String(secret);
        }

        /// <summary>
        /// Vulnerability: Weak backup code generation
        /// </summary>
        public string[] GenerateBackupCodesWeak(int count)
        {
            Random random = new Random((int)DateTime.Now.Ticks);
            string[] codes = new string[count];
            for (int i = 0; i < count; i++)
            {
                StringBuilder code = new StringBuilder();
                for (int j = 0; j < 8; j++)
                {
                    code.Append(random.Next(10));
                }
                codes[i] = code.ToString();
            }
            return codes;
        }

        /// <summary>
        /// Vulnerability: Timing attack in 2FA verification
        /// </summary>
        public bool Verify2FACodeTiming(string code, string expected)
        {
            return code == expected; // Not constant-time
        }
    }

    // ============================================================================
    // OAUTH/OPENID VULNERABILITIES
    // ============================================================================

    public class InsecureOAuthHandler
    {
        /// <summary>
        /// Vulnerability: Weak OAuth state parameter
        /// </summary>
        public string GenerateStateParameterWeak()
        {
            Random random = new Random((int)DateTime.Now.Ticks);
            StringBuilder state = new StringBuilder();
            for (int i = 0; i < 16; i++)
            {
                state.Append(random.Next(10));
            }
            return state.ToString();
        }

        /// <summary>
        /// Vulnerability: Predictable client secret
        /// </summary>
        public string GenerateClientSecretWeak(string clientId)
        {
            string data = $"client_{clientId}";
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(data));
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        /// <summary>
        /// Vulnerability: Weak authorization code
        /// </summary>
        public string GenerateAuthorizationCodeWeak(int userId)
        {
            Random random = new Random(userId);
            byte[] code = new byte[32];
            random.NextBytes(code);
            return Convert.ToBase64String(code);
        }
    }

    // ============================================================================
    // COOKIE SECURITY VULNERABILITIES
    // ============================================================================

    public class InsecureCookieHandler
    {
        // Vulnerability: Hardcoded encryption key
        private static readonly byte[] EncryptionKey = Encoding.UTF8.GetBytes("CookieKey1234567");

        /// <summary>
        /// Vulnerability: Weak cookie encryption
        /// </summary>
        public string EncryptCookieWeak(string value)
        {
            // Vulnerability: Simple XOR (extremely weak)
            byte[] valueBytes = Encoding.UTF8.GetBytes(value);
            byte[] encrypted = new byte[valueBytes.Length];
            for (int i = 0; i < valueBytes.Length; i++)
            {
                encrypted[i] = (byte)(valueBytes[i] ^ EncryptionKey[i % EncryptionKey.Length]);
            }
            return Convert.ToBase64String(encrypted);
        }

        /// <summary>
        /// Vulnerability: Using MD5 for cookie signature
        /// </summary>
        public string SignCookieMD5(string value)
        {
            using (MD5 md5 = MD5.Create())
            {
                byte[] data = Encoding.UTF8.GetBytes(Encoding.UTF8.GetString(EncryptionKey) + value);
                byte[] hash = md5.ComputeHash(data);
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        /// <summary>
        /// Vulnerability: Cookie without Secure flag
        /// </summary>
        public HttpCookie CreateInsecureCookie(string name, string value)
        {
            HttpCookie cookie = new HttpCookie(name, value);
            cookie.HttpOnly = false; // Vulnerable to XSS
            cookie.Secure = false;   // Can be transmitted over HTTP
            return cookie;
        }
    }

    // ============================================================================
    // VIEW STATE VULNERABILITIES
    // ============================================================================

    public class InsecureViewStateHandler
    {
        /// <summary>
        /// Vulnerability: ViewState with weak MAC
        /// </summary>
        public string GenerateViewStateMACWeak(string viewStateData)
        {
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(viewStateData));
                return Convert.ToBase64String(hash);
            }
        }
    }

    // ============================================================================
    // MAIN DEMONSTRATION
    // ============================================================================

    public class Program
    {
        public static void Main(string[] args)
        {
            Console.WriteLine("======================================================================");
            Console.WriteLine("WEB CRYPTO VULNERABILITIES - IBM Quantum Safe Explorer");
            Console.WriteLine("======================================================================");

            // JWT vulnerabilities
            Console.WriteLine("\n[1] JWT VULNERABILITIES:");
            InsecureJWTHandler jwtHandler = new InsecureJWTHandler();
            Console.WriteLine($"   JWT with weak secret: {jwtHandler.CreateJWTWeakSecret(12345)}");

            // Session management vulnerabilities
            Console.WriteLine("\n[2] SESSION MANAGEMENT VULNERABILITIES:");
            InsecureSessionManager sessionMgr = new InsecureSessionManager();
            Console.WriteLine($"   Weak Session Token: {sessionMgr.CreateSessionTokenWeak(12345)}");
            Console.WriteLine($"   MD5 HMAC: {sessionMgr.SignSessionDataMD5("session_data")}");

            // API key vulnerabilities
            Console.WriteLine("\n[3] API KEY GENERATION VULNERABILITIES:");
            InsecureAPIKeyGenerator apiGen = new InsecureAPIKeyGenerator();
            Console.WriteLine($"   Weak Random API Key: {apiGen.GenerateAPIKeyWeakRandom()}");
            Console.WriteLine($"   Predictable API Key: {apiGen.GenerateAPIKeyPredictable(12345)}");

            // Password hashing vulnerabilities
            Console.WriteLine("\n[4] PASSWORD HASHING VULNERABILITIES:");
            InsecurePasswordHasher pwHasher = new InsecurePasswordHasher();
            Console.WriteLine($"   MD5 Password Hash: {pwHasher.HashPasswordMD5("password123")}");
            Console.WriteLine($"   SHA-1 Password Hash: {pwHasher.HashPasswordSHA1("password123")}");

            // Password reset vulnerabilities
            Console.WriteLine("\n[5] PASSWORD RESET TOKEN VULNERABILITIES:");
            InsecurePasswordResetHandler resetHandler = new InsecurePasswordResetHandler();
            Console.WriteLine($"   Weak Reset Token: {resetHandler.GenerateResetTokenWeak("user@example.com")}");

            // 2FA vulnerabilities
            Console.WriteLine("\n[6] TWO-FACTOR AUTHENTICATION VULNERABILITIES:");
            Insecure2FAHandler twoFAHandler = new Insecure2FAHandler();
            Console.WriteLine($"   Weak TOTP Secret: {twoFAHandler.GenerateTOTPSecretWeak()}");
            Console.WriteLine($"   Weak Backup Codes: {string.Join(", ", twoFAHandler.GenerateBackupCodesWeak(5))}");

            // OAuth vulnerabilities
            Console.WriteLine("\n[7] OAUTH VULNERABILITIES:");
            InsecureOAuthHandler oauthHandler = new InsecureOAuthHandler();
            Console.WriteLine($"   Weak State Parameter: {oauthHandler.GenerateStateParameterWeak()}");
            Console.WriteLine($"   Weak Client Secret: {oauthHandler.GenerateClientSecretWeak("client123")}");

            // Cookie vulnerabilities
            Console.WriteLine("\n[8] COOKIE SECURITY VULNERABILITIES:");
            InsecureCookieHandler cookieHandler = new InsecureCookieHandler();
            Console.WriteLine($"   Weak Cookie Encryption: {cookieHandler.EncryptCookieWeak("session_data")}");
            Console.WriteLine($"   MD5 Cookie Signature: {cookieHandler.SignCookieMD5("session_data")}");

            Console.WriteLine("\n======================================================================");
            Console.WriteLine("All web vulnerability tests completed!");
            Console.WriteLine("This file should trigger multiple findings in Quantum Safe Explorer!");
            Console.WriteLine("======================================================================");
        }
    }
}

// Made with Bob