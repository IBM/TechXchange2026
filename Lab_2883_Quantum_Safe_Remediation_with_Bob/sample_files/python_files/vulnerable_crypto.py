#!/usr/bin/env python3
"""
Comprehensive Python cryptographic vulnerabilities for testing IBM Quantum Safe Explorer.
This file contains multiple quantum-vulnerable and weak cryptographic implementations.

WARNING: This code is intentionally insecure and should NOT be used in production!
"""

import hashlib
import random
import time
from Crypto.Cipher import DES, DES3, AES, ARC4, Blowfish
from Crypto.PublicKey import RSA, DSA, ECC
from Crypto.Signature import pkcs1_15, DSS
from Crypto.Hash import MD5, SHA1, SHA256
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64

# ============================================================================
# CATEGORY 1: WEAK HASH ALGORITHMS
# ============================================================================

def weak_hash_md5(data):
    """
    Vulnerability: MD5 hash algorithm (broken, collision attacks)
    """
    md5_hash = hashlib.md5(data.encode()).hexdigest()
    return md5_hash

def weak_hash_sha1(data):
    """
    Vulnerability: SHA-1 hash algorithm (deprecated, collision attacks)
    """
    sha1_hash = hashlib.sha1(data.encode()).hexdigest()
    return sha1_hash

def weak_password_hash_md5(password):
    """
    Vulnerability: Using MD5 for password hashing (no salt, weak algorithm)
    """
    return hashlib.md5(password.encode()).hexdigest()

def weak_password_hash_sha1(password):
    """
    Vulnerability: Using SHA-1 for password hashing
    """
    return hashlib.sha1(password.encode()).hexdigest()

# ============================================================================
# CATEGORY 2: WEAK SYMMETRIC ENCRYPTION
# ============================================================================

def encrypt_with_des(plaintext, key):
    """
    Vulnerability: DES encryption (56-bit key, easily brute-forced)
    """
    cipher = DES.new(key[:8], DES.MODE_ECB)
    padded_text = pad(plaintext.encode(), DES.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return base64.b64encode(ciphertext).decode()

def encrypt_with_3des(plaintext, key):
    """
    Vulnerability: 3DES/Triple DES (quantum vulnerable, deprecated)
    """
    cipher = DES3.new(key[:24], DES3.MODE_ECB)
    padded_text = pad(plaintext.encode(), DES3.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return base64.b64encode(ciphertext).decode()

def encrypt_with_rc4(plaintext, key):
    """
    Vulnerability: RC4 stream cipher (biased, multiple attacks)
    """
    cipher = ARC4.new(key)
    ciphertext = cipher.encrypt(plaintext.encode())
    return base64.b64encode(ciphertext).decode()

def encrypt_with_aes_ecb(plaintext, key):
    """
    Vulnerability: AES with ECB mode (pattern leakage)
    """
    cipher = AES.new(key[:16], AES.MODE_ECB)
    padded_text = pad(plaintext.encode(), AES.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return base64.b64encode(ciphertext).decode()

def encrypt_with_blowfish_weak_key(plaintext):
    """
    Vulnerability: Blowfish with weak key size
    """
    key = b'weak'  # Very weak key
    cipher = Blowfish.new(key, Blowfish.MODE_ECB)
    padded_text = pad(plaintext.encode(), Blowfish.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return base64.b64encode(ciphertext).decode()

def encrypt_with_static_iv(plaintext, key):
    """
    Vulnerability: Using static/hardcoded IV
    """
    static_iv = b'\x00' * 16  # Hardcoded IV - major security flaw
    cipher = AES.new(key[:16], AES.MODE_CBC, static_iv)
    padded_text = pad(plaintext.encode(), AES.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return base64.b64encode(ciphertext).decode()

# ============================================================================
# CATEGORY 3: WEAK ASYMMETRIC CRYPTOGRAPHY (QUANTUM VULNERABLE)
# ============================================================================

def generate_rsa_512():
    """
    Vulnerability: RSA with 512-bit key (extremely weak)
    """
    key = RSA.generate(512)
    return key

def generate_rsa_1024():
    """
    Vulnerability: RSA with 1024-bit key (insufficient, quantum vulnerable)
    """
    key = RSA.generate(1024)
    return key

def generate_rsa_2048():
    """
    Vulnerability: RSA with 2048-bit key (quantum vulnerable)
    """
    key = RSA.generate(2048)
    return key

def sign_with_rsa(message, private_key):
    """
    Vulnerability: RSA signature (quantum vulnerable)
    """
    h = SHA256.new(message.encode())
    signature = pkcs1_15.new(private_key).sign(h)
    return base64.b64encode(signature).decode()

def generate_dsa_1024():
    """
    Vulnerability: DSA with 1024-bit key (quantum vulnerable)
    """
    key = DSA.generate(1024)
    return key

def sign_with_dsa(message, private_key):
    """
    Vulnerability: DSA signature (quantum vulnerable)
    """
    h = SHA256.new(message.encode())
    signer = DSS.new(private_key, 'fips-186-3')
    signature = signer.sign(h)
    return base64.b64encode(signature).decode()

def generate_ecc_p256():
    """
    Vulnerability: ECC P-256 curve (quantum vulnerable)
    """
    key = ECC.generate(curve='P-256')
    return key

def generate_ecc_p384():
    """
    Vulnerability: ECC P-384 curve (quantum vulnerable)
    """
    key = ECC.generate(curve='P-384')
    return key

def sign_with_ecdsa(message, private_key):
    """
    Vulnerability: ECDSA signature (quantum vulnerable)
    """
    h = SHA256.new(message.encode())
    signer = DSS.new(private_key, 'fips-186-3')
    signature = signer.sign(h)
    return base64.b64encode(signature).decode()

# ============================================================================
# CATEGORY 4: INSECURE RANDOM NUMBER GENERATION
# ============================================================================

def insecure_random_python():
    """
    Vulnerability: Using Python's random module for cryptographic purposes
    """
    return random.randint(0, 1000000)

def insecure_random_with_seed():
    """
    Vulnerability: Using predictable seed
    """
    random.seed(12345)  # Fixed seed - completely predictable
    return random.randint(0, 1000000)

def insecure_random_time_seed():
    """
    Vulnerability: Using time as seed (predictable)
    """
    random.seed(int(time.time()))
    return random.randint(0, 1000000)

def insecure_key_generation():
    """
    Vulnerability: Generating cryptographic key with weak random
    """
    random.seed(42)
    key = bytes([random.randint(0, 255) for _ in range(16)])
    return key

# ============================================================================
# CATEGORY 5: HARDCODED SECRETS
# ============================================================================

# Vulnerability: Hardcoded encryption key
HARDCODED_KEY = b'SuperSecretKey16'

# Vulnerability: Hardcoded IV
HARDCODED_IV = b'InitVector123456'

# Vulnerability: Hardcoded password
HARDCODED_PASSWORD = 'admin123'

def encrypt_with_hardcoded_key(plaintext):
    """
    Vulnerability: Using hardcoded key for encryption
    """
    cipher = AES.new(HARDCODED_KEY, AES.MODE_CBC, HARDCODED_IV)
    padded_text = pad(plaintext.encode(), AES.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return base64.b64encode(ciphertext).decode()

# ============================================================================
# CATEGORY 6: INSUFFICIENT KEY LENGTHS
# ============================================================================

def generate_aes_128_key():
    """
    Vulnerability: AES with 128-bit key (minimum, not recommended for quantum safety)
    """
    return get_random_bytes(16)  # 128 bits

def generate_weak_des_key():
    """
    Vulnerability: DES key (only 56 effective bits)
    """
    return get_random_bytes(8)

# ============================================================================
# CATEGORY 7: MULTIPLE COMBINED VULNERABILITIES
# ============================================================================

def multiple_vulnerabilities_example(plaintext):
    """
    Multiple vulnerabilities combined:
    - Weak random number generation
    - Insufficient key length
    - Weak algorithm (DES)
    - ECB mode
    """
    random.seed(123)  # Weak random
    key = bytes([random.randint(0, 255) for _ in range(8)])  # Weak key generation
    cipher = DES.new(key, DES.MODE_ECB)  # Weak algorithm + ECB mode
    padded_text = pad(plaintext.encode(), DES.block_size)
    ciphertext = cipher.encrypt(padded_text)
    return base64.b64encode(ciphertext).decode()

# ============================================================================
# MAIN DEMONSTRATION
# ============================================================================

def main():
    print("=" * 70)
    print("CRYPTOGRAPHIC VULNERABILITIES TEST - IBM Quantum Safe Explorer")
    print("=" * 70)
    
    test_data = "Sensitive Information"
    test_password = "password123"
    
    print("\n[1] WEAK HASH ALGORITHMS:")
    print(f"   MD5 Hash: {weak_hash_md5(test_data)}")
    print(f"   SHA-1 Hash: {weak_hash_sha1(test_data)}")
    print(f"   MD5 Password Hash: {weak_password_hash_md5(test_password)}")
    
    print("\n[2] WEAK SYMMETRIC ENCRYPTION:")
    des_key = b'8bytekey'
    print(f"   DES Encrypted: {encrypt_with_des(test_data, des_key)}")
    print(f"   3DES Encrypted: {encrypt_with_3des(test_data, des_key * 3)}")
    print(f"   RC4 Encrypted: {encrypt_with_rc4(test_data, des_key)}")
    print(f"   AES-ECB Encrypted: {encrypt_with_aes_ecb(test_data, b'16ByteAESKey1234')}")
    
    print("\n[3] QUANTUM-VULNERABLE ASYMMETRIC CRYPTO:")
    rsa_512 = generate_rsa_512()
    print(f"   RSA-512 key generated: {rsa_512.n.bit_length()} bits")
    rsa_1024 = generate_rsa_1024()
    print(f"   RSA-1024 key generated: {rsa_1024.n.bit_length()} bits")
    rsa_2048 = generate_rsa_2048()
    print(f"   RSA-2048 key generated: {rsa_2048.n.bit_length()} bits")
    
    dsa_key = generate_dsa_1024()
    print(f"   DSA-1024 key generated")
    
    ecc_key = generate_ecc_p256()
    print(f"   ECC P-256 key generated")
    
    print("\n[4] INSECURE RANDOM NUMBER GENERATION:")
    print(f"   Insecure random: {insecure_random_python()}")
    print(f"   Predictable seed random: {insecure_random_with_seed()}")
    print(f"   Time-based seed random: {insecure_random_time_seed()}")
    
    print("\n[5] HARDCODED SECRETS:")
    print(f"   Hardcoded key: {HARDCODED_KEY}")
    print(f"   Encrypted with hardcoded key: {encrypt_with_hardcoded_key(test_data)}")
    
    print("\n[6] COMBINED VULNERABILITIES:")
    print(f"   Multiple vulnerabilities: {multiple_vulnerabilities_example(test_data)}")
    
    print("\n" + "=" * 70)
    print("All vulnerability tests completed!")
    print("This file should trigger multiple findings in Quantum Safe Explorer!")
    print("=" * 70)

if __name__ == "__main__":
    main()

# Made with Bob