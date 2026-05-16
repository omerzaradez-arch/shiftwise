"""
Run once locally to generate VAPID keys.
Set the output as VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY in Railway.

Usage:
    cd backend
    python generate_vapid.py
"""
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend


def b64urlsafe(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def main():
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    # Private key — PEM format (pywebpush accepts this)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Public key — uncompressed point (65 bytes), then base64url-encoded
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = b64urlsafe(pub_bytes)

    print("=" * 60)
    print("VAPID Keys generated successfully!")
    print("=" * 60)
    print()
    print("Add these to your Railway backend Variables:")
    print()
    print("VAPID_PUBLIC_KEY:")
    print(pub_b64)
    print()
    print("VAPID_PRIVATE_KEY: (copy ALL lines including BEGIN/END)")
    print(priv_pem.decode())
    print()
    print("VAPID_CONTACT_EMAIL:")
    print("mailto:omerzaradez@gmail.com")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
