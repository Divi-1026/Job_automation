from cryptography.fernet import Fernet
import os

# Generate a key once and store in environment variable FERNET_KEY
# Run: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("FERNET_KEY environment variable not set")
cipher = Fernet(FERNET_KEY.encode())

def encrypt_password(password: str) -> str:
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()