from cryptography.fernet import (
    Fernet,
    InvalidToken,
)

from app.core.config import settings


FERNET_KEY = settings.FERNET_KEY


if not FERNET_KEY:
    raise RuntimeError(
        "FERNET_KEY is not configured."
    )


try:
    cipher = Fernet(
        FERNET_KEY.encode("utf-8")
    )

except Exception as exc:
    raise RuntimeError(
        "FERNET_KEY is invalid."
    ) from exc


def encrypt_password(
    password: str
) -> str:

    if not password:
        raise ValueError(
            "Password cannot be empty."
        )

    encrypted = cipher.encrypt(
        password.encode("utf-8")
    )

    return encrypted.decode("utf-8")


def decrypt_password(
    encrypted_password: str
) -> str:

    if not encrypted_password:
        raise ValueError(
            "Encrypted password cannot be empty."
        )

    try:
        decrypted = cipher.decrypt(
            encrypted_password.encode("utf-8")
        )

        return decrypted.decode("utf-8")

    except InvalidToken as exc:
        raise ValueError(
            "Could not decrypt platform credentials."
        ) from exc