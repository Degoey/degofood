"""Keamanan portal merchant: hashing password, token sesi, rate limit, ownership.

- Password: scrypt (fallback PBKDF2-HMAC-SHA256) dengan salt acak per akun.
- Token: 32 byte acak (secrets.token_urlsafe); yang disimpan di DB hanya SHA-256.
- Rate limit login: dihitung dari tabel merchant_auth_events (fail closed).
- Otorisasi: setiap resource merchant diverifikasi lewat restaurant_id akun.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import merchant_models as mm

SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
PBKDF2_ROUNDS = 260000

TOKEN_TTL_HOURS = int(os.getenv('MERCHANT_TOKEN_TTL_HOURS', '12'))
LOGIN_MAX_FAILS = int(os.getenv('MERCHANT_LOGIN_MAX_FAILS', '5'))
LOGIN_WINDOW_SECONDS = int(os.getenv('MERCHANT_LOGIN_WINDOW_SECONDS', '900'))


# --------------------------------------------------------------------------- #
# Password
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Hash password. Format: scrypt$n$r$p$salt_hex$hash_hex (atau pbkdf2$...)."""
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError('password minimal 8 karakter')
    salt = secrets.token_bytes(16)
    try:
        digest = hashlib.scrypt(password.encode('utf-8'), salt=salt,
                                n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
        return f'scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}'
    except (ValueError, AttributeError):  # scrypt tidak tersedia di build Python ini
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ROUNDS, dklen=32)
        return f'pbkdf2${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, stored: str) -> bool:
    """Verifikasi password terhadap hash tersimpan (konstan waktu)."""
    try:
        parts = (stored or '').split('$')
        if parts[0] == 'scrypt' and len(parts) == 6:
            _, n, r, p, salt_hex, hash_hex = parts
            digest = hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt_hex),
                                    n=int(n), r=int(r), p=int(p), dklen=len(bytes.fromhex(hash_hex)))
        elif parts[0] == 'pbkdf2' and len(parts) == 4:
            _, rounds, salt_hex, hash_hex = parts
            digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                         bytes.fromhex(salt_hex), int(rounds),
                                         dklen=len(bytes.fromhex(hash_hex)))
        else:
            return False
        return hmac.compare_digest(digest.hex(), hash_hex)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Token sesi
# --------------------------------------------------------------------------- #
def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def issue_token(db: Session, account: mm.MerchantAccount, label: Optional[str] = None):
    """Buat token sesi baru. Mengembalikan (raw_token, expires_at)."""
    raw = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
    db.add(mm.MerchantToken(account_id=account.id, token_hash=hash_token(raw),
                            expires_at=expires_at, label=(label or '')[:80] or None))
    account.last_login_at = datetime.utcnow()
    db.commit()
    return raw, expires_at


def revoke_token(db: Session, raw_token: str) -> bool:
    row = db.query(mm.MerchantToken).filter(mm.MerchantToken.token_hash == hash_token(raw_token)).first()
    if not row:
        return False
    row.revoked = True
    db.commit()
    return True


# --------------------------------------------------------------------------- #
# Rate limit login
# --------------------------------------------------------------------------- #
def _window_start() -> datetime:
    return datetime.utcnow() - timedelta(seconds=LOGIN_WINDOW_SECONDS)


def login_blocked(db: Session, identifier: str, ip: Optional[str]) -> bool:
    """True kalau percobaan gagal terakhir sudah melewati batas (fail closed)."""
    q = db.query(mm.MerchantAuthEvent).filter(
        mm.MerchantAuthEvent.success == False,  # noqa: E712
        mm.MerchantAuthEvent.created_at >= _window_start(),
        mm.MerchantAuthEvent.identifier == (identifier or '').lower(),
    )
    return q.count() >= LOGIN_MAX_FAILS


def record_login_attempt(db: Session, identifier: str, ip: Optional[str], success: bool):
    db.add(mm.MerchantAuthEvent(identifier=(identifier or '').lower(), ip=ip, success=success))
    db.commit()


# --------------------------------------------------------------------------- #
# Dependency: akun merchant dari Bearer token
# --------------------------------------------------------------------------- #
def _bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1].strip()


def get_current_account(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> mm.MerchantAccount:
    """Resolve akun merchant dari token. 401 kalau token hilang/expired/revoked."""
    raw = _bearer(authorization)
    if not raw:
        raise HTTPException(status_code=401, detail='Token merchant wajib dikirim (Bearer).')
    row = db.query(mm.MerchantToken).filter(mm.MerchantToken.token_hash == hash_token(raw)).first()
    if not row or row.revoked or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail='Token tidak valid atau kedaluwarsa.')
    account = db.query(mm.MerchantAccount).filter(mm.MerchantAccount.id == row.account_id).first()
    if not account or not account.is_active:
        raise HTTPException(status_code=401, detail='Akun merchant tidak aktif.')
    return account


def owned_restaurant_id(account: mm.MerchantAccount) -> int:
    if not account.restaurant_id:
        raise HTTPException(status_code=403, detail='Akun belum terhubung ke restoran.')
    return account.restaurant_id


def get_owned_menu(db: Session, account: mm.MerchantAccount, menu_id: int):
    """Ambil menu HANYA kalau milik restoran akun ini (isolasi antar merchant)."""
    from . import models
    menu = db.query(models.Menu).filter(
        models.Menu.id == menu_id,
        models.Menu.restaurant_id == owned_restaurant_id(account),
    ).first()
    if not menu:
        raise HTTPException(status_code=404, detail='Menu tidak ditemukan untuk restoran Anda.')
    return menu


def get_owned_order(db: Session, account: mm.MerchantAccount, order_id: int):
    from . import models
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.restaurant_id == owned_restaurant_id(account),
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail='Pesanan tidak ditemukan untuk restoran Anda.')
    return order
