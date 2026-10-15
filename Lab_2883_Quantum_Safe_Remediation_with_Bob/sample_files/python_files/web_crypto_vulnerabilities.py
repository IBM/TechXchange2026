#!/usr/bin/env python3
"""
Python Web Framework Cryptographic Vulnerabilities (Django/Flask)
Testing file for IBM Quantum Safe Explorer

WARNING: This code is intentionally insecure and should NOT be used in production!
"""

import hashlib
import hmac
import secrets
import random
import jwt
from datetime import datetime, timedelta
import base64

# ============================================================================
# DJANGO-STYLE VULNERABILITIES
# ============================================================================

class InsecureDjangoPasswordHasher:
    """
    Vulnerability: Custom password hasher using weak algorithms
    """
    
    def hash_password_md5(self, password, salt=None):
        """Vulnerability: MD5 for password hashing"""
        if not salt:
            salt = str(random.randint(1000, 9999))  # Weak random
        return hashlib.md5(f"{salt}{password}".encode()).hexdigest()
    
    def hash_password_sha1(self, password, salt=None):
        """Vulnerability: SHA-1 for password hashing"""
        if not salt:
            salt = str(random.randint(1000, 9999))
        return hashlib.sha1(f"{salt}{password}".encode()).hexdigest()
    
    def verify_password_timing_attack(self, password, hashed):
        """Vulnerability: Timing attack in password comparison"""
        return self.hash_password_md5(password) == hashed  # Not constant-time

# ============================================================================
# FLASK-STYLE SESSION VULNERABILITIES
# ============================================================================

class InsecureFlaskSession:
    """
    Vulnerability: Weak session management
    """
    
    # Vulnerability: Hardcoded secret key
    SECRET_KEY = "hardcoded-secret-key-123"
    
    def __init__(self):
        self.secret = self.SECRET_KEY
    
    def create_session_token_weak(self, user_id):
        """Vulnerability: Weak session token generation"""
        random.seed(user_id)  # Predictable
        token = ''.join([str(random.randint(0, 9)) for _ in range(32)])
        return token
    
    def sign_data_md5(self, data):
        """Vulnerability: Using MD5 for HMAC"""
        return hmac.new(
            self.secret.encode(),
            data.encode(),
            hashlib.md5
        ).hexdigest()
    
    def sign_data_sha1(self, data):
        """Vulnerability: Using SHA-1 for HMAC"""
        return hmac.new(
            self.secret.encode(),
            data.encode(),
            hashlib.sha1
        ).hexdigest()

# ============================================================================
# JWT VULNERABILITIES
# ============================================================================

class InsecureJWTHandler:
    """
    Vulnerability: Weak JWT implementation
    """
    
    # Vulnerability: Weak secret key
    JWT_SECRET = "weak_secret"
    
    def create_jwt_none_algorithm(self, payload):
        """Vulnerability: JWT with 'none' algorithm"""
        header = base64.b64encode(b'{"alg":"none","typ":"JWT"}').decode()
        payload_encoded = base64.b64encode(str(payload).encode()).decode()
        return f"{header}.{payload_encoded}."
    
    def create_jwt_weak_secret(self, user_id):
        """Vulnerability: JWT with weak secret"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.JWT_SECRET, algorithm='HS256')
    
    def create_jwt_no_expiration(self, user_id):
        """Vulnerability: JWT without expiration"""
        payload = {'user_id': user_id}
        return jwt.encode(payload, self.JWT_SECRET, algorithm='HS256')
    
    def create_jwt_rsa_weak(self, user_id, private_key):
        """Vulnerability: JWT with RSA (quantum vulnerable)"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, private_key, algorithm='RS256')

# ============================================================================
# API KEY GENERATION VULNERABILITIES
# ============================================================================

class InsecureAPIKeyGenerator:
    """
    Vulnerability: Weak API key generation
    """
    
    def generate_api_key_weak_random(self):
        """Vulnerability: Using weak random for API keys"""
        random.seed(int(datetime.now().timestamp()))
        return ''.join([hex(random.randint(0, 15))[2:] for _ in range(32)])
    
    def generate_api_key_predictable(self, user_id):
        """Vulnerability: Predictable API key based on user ID"""
        return hashlib.md5(f"api_key_{user_id}".encode()).hexdigest()
    
    def generate_api_key_sequential(self, counter):
        """Vulnerability: Sequential API keys"""
        return f"API-{counter:08d}"

# ============================================================================
# COOKIE SECURITY VULNERABILITIES
# ============================================================================

class InsecureCookieHandler:
    """
    Vulnerability: Insecure cookie handling
    """
    
    def create_cookie_no_secure_flag(self, name, value):
        """Vulnerability: Cookie without Secure flag"""
        return {
            'name': name,
            'value': value,
            'httponly': False,  # Vulnerable to XSS
            'secure': False,    # Can be transmitted over HTTP
            'samesite': 'None'  # CSRF vulnerable
        }
    
    def encrypt_cookie_weak(self, value):
        """Vulnerability: Weak cookie encryption"""
        key = b'8bytekey'  # Weak key
        # Simulated weak encryption
        return base64.b64encode(value.encode()).decode()

# ============================================================================
# DATABASE ENCRYPTION VULNERABILITIES
# ============================================================================

class InsecureDatabaseEncryption:
    """
    Vulnerability: Weak database field encryption
    """
    
    # Vulnerability: Hardcoded encryption key
    DB_ENCRYPTION_KEY = b'DatabaseKey12345'
    
    def encrypt_field_weak(self, plaintext):
        """Vulnerability: Weak field encryption (simulated)"""
        # Using simple XOR (extremely weak)
        key = self.DB_ENCRYPTION_KEY
        encrypted = bytes([plaintext.encode()[i % len(plaintext)] ^ key[i % len(key)] 
                          for i in range(len(plaintext))])
        return base64.b64encode(encrypted).decode()
    
    def hash_sensitive_data_md5(self, data):
        """Vulnerability: MD5 for sensitive data hashing"""
        return hashlib.md5(data.encode()).hexdigest()

# ============================================================================
# PASSWORD RESET TOKEN VULNERABILITIES
# ============================================================================

class InsecurePasswordResetHandler:
    """
    Vulnerability: Weak password reset tokens
    """
    
    def generate_reset_token_weak(self, email):
        """Vulnerability: Predictable reset token"""
        timestamp = int(datetime.now().timestamp())
        return hashlib.md5(f"{email}{timestamp}".encode()).hexdigest()
    
    def generate_reset_token_no_expiry(self, user_id):
        """Vulnerability: Reset token without expiration"""
        random.seed(user_id)
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    def verify_reset_token_timing(self, token, expected):
        """Vulnerability: Timing attack in token verification"""
        return token == expected  # Not constant-time comparison

# ============================================================================
# FILE UPLOAD ENCRYPTION VULNERABILITIES
# ============================================================================

class InsecureFileEncryption:
    """
    Vulnerability: Weak file encryption
    """
    
    def encrypt_file_weak_key(self, file_content):
        """Vulnerability: File encryption with weak key"""
        key = b'weak'  # Very weak key
        # Simulated weak encryption
        return base64.b64encode(file_content).decode()
    
    def generate_file_hash_md5(self, file_content):
        """Vulnerability: MD5 for file integrity"""
        return hashlib.md5(file_content).hexdigest()

# ============================================================================
# TWO-FACTOR AUTHENTICATION VULNERABILITIES
# ============================================================================

class Insecure2FAHandler:
    """
    Vulnerability: Weak 2FA implementation
    """
    
    def generate_totp_secret_weak(self):
        """Vulnerability: Weak TOTP secret generation"""
        random.seed(42)
        return base64.b32encode(
            bytes([random.randint(0, 255) for _ in range(10)])
        ).decode()
    
    def generate_backup_codes_weak(self, count=10):
        """Vulnerability: Weak backup code generation"""
        random.seed(int(datetime.now().timestamp()))
        codes = []
        for _ in range(count):
            code = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            codes.append(code)
        return codes
    
    def verify_2fa_code_timing(self, code, expected):
        """Vulnerability: Timing attack in 2FA verification"""
        return code == expected  # Not constant-time

# ============================================================================
# OAUTH/OPENID VULNERABILITIES
# ============================================================================

class InsecureOAuthHandler:
    """
    Vulnerability: Weak OAuth implementation
    """
    
    def generate_state_parameter_weak(self):
        """Vulnerability: Weak OAuth state parameter"""
        random.seed(int(datetime.now().timestamp()))
        return ''.join([str(random.randint(0, 9)) for _ in range(16)])
    
    def generate_client_secret_weak(self, client_id):
        """Vulnerability: Predictable client secret"""
        return hashlib.md5(f"client_{client_id}".encode()).hexdigest()

# ============================================================================
# MAIN DEMONSTRATION
# ============================================================================

def main():
    print("=" * 70)
    print("WEB FRAMEWORK CRYPTO VULNERABILITIES - IBM Quantum Safe Explorer")
    print("=" * 70)
    
    # Django vulnerabilities
    print("\n[1] DJANGO PASSWORD HASHING VULNERABILITIES:")
    django_hasher = InsecureDjangoPasswordHasher()
    print(f"   MD5 Password Hash: {django_hasher.hash_password_md5('password123')}")
    print(f"   SHA-1 Password Hash: {django_hasher.hash_password_sha1('password123')}")
    
    # Flask session vulnerabilities
    print("\n[2] FLASK SESSION VULNERABILITIES:")
    flask_session = InsecureFlaskSession()
    print(f"   Weak Session Token: {flask_session.create_session_token_weak(12345)}")
    print(f"   MD5 HMAC: {flask_session.sign_data_md5('session_data')}")
    
    # JWT vulnerabilities
    print("\n[3] JWT VULNERABILITIES:")
    jwt_handler = InsecureJWTHandler()
    print(f"   JWT with 'none' algorithm: {jwt_handler.create_jwt_none_algorithm({'user': 1})}")
    print(f"   JWT with weak secret: {jwt_handler.create_jwt_weak_secret(12345)}")
    
    # API key vulnerabilities
    print("\n[4] API KEY GENERATION VULNERABILITIES:")
    api_gen = InsecureAPIKeyGenerator()
    print(f"   Weak Random API Key: {api_gen.generate_api_key_weak_random()}")
    print(f"   Predictable API Key: {api_gen.generate_api_key_predictable(12345)}")
    
    # Password reset vulnerabilities
    print("\n[5] PASSWORD RESET TOKEN VULNERABILITIES:")
    reset_handler = InsecurePasswordResetHandler()
    print(f"   Weak Reset Token: {reset_handler.generate_reset_token_weak('user@example.com')}")
    
    # 2FA vulnerabilities
    print("\n[6] TWO-FACTOR AUTHENTICATION VULNERABILITIES:")
    twofa_handler = Insecure2FAHandler()
    print(f"   Weak TOTP Secret: {twofa_handler.generate_totp_secret_weak()}")
    print(f"   Weak Backup Codes: {twofa_handler.generate_backup_codes_weak(5)}")
    
    # OAuth vulnerabilities
    print("\n[7] OAUTH VULNERABILITIES:")
    oauth_handler = InsecureOAuthHandler()
    print(f"   Weak State Parameter: {oauth_handler.generate_state_parameter_weak()}")
    print(f"   Weak Client Secret: {oauth_handler.generate_client_secret_weak('client123')}")
    
    print("\n" + "=" * 70)
    print("All web framework vulnerability tests completed!")
    print("This file should trigger multiple findings in Quantum Safe Explorer!")
    print("=" * 70)

if __name__ == "__main__":
    main()

# Made with Bob