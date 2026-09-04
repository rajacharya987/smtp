"""DKIM key generation. Private keys stay on disk and are never returned by default."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from mailgate.paths import DKIM_DIR
from mailgate.validate import normalize_domain


def _paths(domain: str, selector: str) -> tuple[Path, Path]:
    name = normalize_domain(domain)
    folder = DKIM_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    private = folder / f"{selector}.private.pem"
    public = folder / f"{selector}.public.pem"
    return private, public


def generate_keypair(domain: str, selector: str = "mail", bits: int = 2048) -> dict:
    private_path, public_path = _paths(domain, selector)
    if private_path.exists():
        return public_record(domain, selector)

    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path.write_bytes(private_bytes)
    private_path.chmod(0o600)
    public_path.write_bytes(public_bytes)
    public_path.chmod(0o644)
    return public_record(domain, selector)


def _public_key_dns(public_pem: bytes) -> str:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    key = load_pem_public_key(public_pem)
    der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # DKIM wants the raw RSA modulus key in base64 from PKCS#1, not SubjectPublicKeyInfo.
    pkcs1 = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.PKCS1,
    )
    import base64

    b64 = base64.b64encode(pkcs1).decode("ascii")
    return b64


def public_record(domain: str, selector: str = "mail") -> dict:
    private_path, public_path = _paths(domain, selector)
    exists = private_path.exists() and public_path.exists()
    txt = None
    if exists:
        txt_key = _public_key_dns(public_path.read_bytes())
        txt = f"v=DKIM1; k=rsa; p={txt_key}"
    name = normalize_domain(domain)
    return {
        "domain": name,
        "selector": selector,
        "dns_name": f"{selector}._domainkey.{name}",
        "txt": txt,
        "private_key_path": str(private_path),
        "private_key_present": private_path.exists(),
        "note": "The private key is stored on disk and is never shown in the dashboard.",
    }
