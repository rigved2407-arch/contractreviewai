import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings


def _derive_key() -> bytes:
    password = settings.encryption_key.encode() if settings.encryption_key else b"insecure-default-change-me"
    salt = settings.encryption_salt.encode() if settings.encryption_salt else b"contract-review-ai-salt"
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000)
    return base64.urlsafe_b64encode(kdf.derive(password))


def get_cipher() -> Fernet:
    return Fernet(_derive_key())


def encrypt_file_bytes(data: bytes) -> bytes:
    cipher = get_cipher()
    return cipher.encrypt(data)


def decrypt_file_bytes(data: bytes) -> bytes:
    cipher = get_cipher()
    return cipher.decrypt(data)


def encrypt_file_at_rest(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        return file_path
    with open(path, "rb") as f:
        plaintext = f.read()
    ciphertext = encrypt_file_bytes(plaintext)
    encrypted_path = path.with_suffix(path.suffix + ".enc")
    with open(encrypted_path, "wb") as f:
        f.write(ciphertext)
    path.unlink()
    return str(encrypted_path)


def decrypt_file_to_temp(encrypted_path: str) -> str:
    path = Path(encrypted_path)
    if not path.suffix == ".enc":
        return encrypted_path
    with open(path, "rb") as f:
        ciphertext = f.read()
    plaintext = decrypt_file_bytes(ciphertext)
    decrypted_path = path.with_suffix("")
    with open(decrypted_path, "wb") as f:
        f.write(plaintext)
    return str(decrypted_path)


def encrypt_text(text: str) -> str:
    cipher = get_cipher()
    return cipher.encrypt(text.encode()).decode()


def decrypt_text(encrypted: str) -> str:
    cipher = get_cipher()
    return cipher.decrypt(encrypted.encode()).decode()
