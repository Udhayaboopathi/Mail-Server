from __future__ import annotations

from typing import Any

from cryptography.fernet import Fernet
from pgpy import PGPKey, PGPMessage, PGPUID
from pgpy.constants import CompressionAlgorithm, HashAlgorithm, KeyFlags, PubKeyAlgorithm, SymmetricKeyAlgorithm
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.encryption_secret_key.encode("utf-8"))


async def generate_pgp_keypair(mailbox_id: str, passphrase: str, db: AsyncSession) -> dict:
    mailbox_row = await db.execute(
        text("SELECT full_address FROM mailboxes WHERE id = :mailbox_id"), {"mailbox_id": mailbox_id}
    )
    mailbox = mailbox_row.mappings().first()
    if mailbox is None:
        raise ValueError("Mailbox not found")

    key = PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, 4096)
    uid = PGPUID.new(mailbox["full_address"])
    key.add_uid(
        uid,
        usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
        hashes=[HashAlgorithm.SHA256],
        ciphers=[SymmetricKeyAlgorithm.AES256],
        compression=[CompressionAlgorithm.ZLIB],
    )
    key.protect(passphrase, SymmetricKeyAlgorithm.AES256, HashAlgorithm.SHA256)

    public_key = str(key.pubkey)
    private_key = str(key)
    encrypted_private_key = _get_fernet().encrypt(private_key.encode("utf-8")).decode("utf-8")
    fingerprint = key.fingerprint

    await db.execute(
        text(
            """
            INSERT INTO pgp_keys (mailbox_id, public_key, private_key_encrypted, fingerprint, is_enabled)
            VALUES (:mailbox_id, :public_key, :private_key_encrypted, :fingerprint, false)
            ON CONFLICT (mailbox_id)
            DO UPDATE SET
                public_key = EXCLUDED.public_key,
                private_key_encrypted = EXCLUDED.private_key_encrypted,
                fingerprint = EXCLUDED.fingerprint,
                is_enabled = false
            """
        ),
        {
            "mailbox_id": mailbox_id,
            "public_key": public_key,
            "private_key_encrypted": encrypted_private_key,
            "fingerprint": fingerprint,
        },
    )
    await db.commit()
    return {"fingerprint": fingerprint, "public_key_armored": public_key}


async def encrypt_message(recipient_public_key: str, plaintext: str) -> str:
    public_key, _ = PGPKey.from_blob(recipient_public_key)
    message = PGPMessage.new(plaintext)
    encrypted = public_key.encrypt(message)
    return str(encrypted)


async def decrypt_message(mailbox_id: str, ciphertext: str, passphrase: str, db: AsyncSession) -> str:
    result = await db.execute(
        text("SELECT private_key_encrypted FROM pgp_keys WHERE mailbox_id = :mailbox_id"),
        {"mailbox_id": mailbox_id},
    )
    row = result.mappings().first()
    if row is None:
        raise ValueError("PGP key not found")

    private_key_armored = _get_fernet().decrypt(str(row["private_key_encrypted"]).encode("utf-8")).decode("utf-8")
    key, _ = PGPKey.from_blob(private_key_armored)
    message = PGPMessage.from_blob(ciphertext)
    with key.unlock(passphrase):
        decrypted = key.decrypt(message)
    return str(decrypted.message)


async def get_public_key(mailbox_id: str, db: AsyncSession) -> str | None:
    result = await db.execute(
        text("SELECT public_key, is_enabled FROM pgp_keys WHERE mailbox_id = :mailbox_id"),
        {"mailbox_id": mailbox_id},
    )
    row = result.mappings().first()
    if row is None or not row["is_enabled"]:
        return None
    return str(row["public_key"])
