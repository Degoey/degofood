"""Endpoint ADMIN untuk portal merchant: provisioning akun, settlement, review pencairan.

Semua endpoint WAJIB header `X-Admin-Key` yang cocok dengan env `ADMIN_API_KEY`
(fail closed: kalau env kosong, semua request ditolak 503).

Catatan jujur soal uang:
- Settlement per order dibuat admin, lalu disetujui admin. Ledger hanya ditulis saat
  approve, dengan `ref` unik => idempoten (approve dua kali tidak menggandakan saldo).
- Pencairan TIDAK dikirim otomatis. Status `paid` = admin sudah transfer manual dan
  menandainya; saat itu barulah ledger didebit.
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import merchant_models as mm
from .. import merchant_schemas as ms
from .. import models
from ..merchant_security import hash_password

router = APIRouter(tags=['Admin Merchant'])


def _require_admin_key(x_admin_key: Optional[str] = Header(default=None)):
    expected = (os.getenv('ADMIN_API_KEY') or '').strip()
    if not expected:
        raise HTTPException(status_code=503,
                            detail='ADMIN_API_KEY belum diset di server; endpoint admin ditutup.')
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail='Admin API key tidak valid.')
    return x_admin_key


def _norm_phone(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if digits.startswith('62'):
        digits = digits[2:]
    elif digits.startswith('0'):
        digits = digits[1:]
    return f'+62{digits}' if digits else None


def _norm_email(raw: Optional[str]) -> Optional[str]:
    value = (raw or '').strip().lower()
    return value or None


def _merchant_payload(account: mm.MerchantAccount) -> dict:
    return {
        'id': account.id, 'restaurant_id': account.restaurant_id, 'name': account.name,
        'phone': account.phone, 'email': account.email, 'is_active': account.is_active,
        'created_at': account.created_at, 'last_login_at': account.last_login_at,
    }


# --------------------------------------------------------------------------- #
# Provisioning akun merchant
# --------------------------------------------------------------------------- #
@router.get('/merchants', response_model=List[ms.AdminMerchantResponse])
def admin_list_merchants(db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    rows = db.query(mm.MerchantAccount).order_by(mm.MerchantAccount.id).all()
    return [_merchant_payload(a) for a in rows]


@router.post('/merchants', response_model=ms.AdminMerchantResponse, status_code=201)
def admin_create_merchant(payload: ms.AdminMerchantCreate, db: Session = Depends(get_db),
                          _=Depends(_require_admin_key)):
    """Buat akun login merchant untuk sebuah restoran.

    Nomor HP restoran TIDAK otomatis dianggap milik merchant: admin harus mengirim
    `restaurant_phone_verified=true` kalau memang sudah diverifikasi ke pemiliknya.
    """
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == payload.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail='Restoran tidak ditemukan.')

    phone = _norm_phone(payload.phone)
    email = _norm_email(payload.email)
    if not phone and not email:
        raise HTTPException(status_code=422, detail='Isi minimal nomor HP atau email.')
    if phone and not payload.restaurant_phone_verified and _norm_phone(restaurant.phone) == phone:
        raise HTTPException(
            status_code=409,
            detail='Nomor HP sama dengan nomor restoran. Kirim restaurant_phone_verified=true '
                   'hanya setelah kepemilikan nomor itu dikonfirmasi ke pemilik toko.')

    if db.query(mm.MerchantAccount).filter(mm.MerchantAccount.restaurant_id == payload.restaurant_id).first():
        raise HTTPException(status_code=409, detail='Restoran ini sudah punya akun merchant.')
    if phone and db.query(mm.MerchantAccount).filter(mm.MerchantAccount.phone == phone).first():
        raise HTTPException(status_code=409, detail=f'Nomor HP {phone} sudah dipakai akun lain.')
    if email and db.query(mm.MerchantAccount).filter(mm.MerchantAccount.email == email).first():
        raise HTTPException(status_code=409, detail=f'Email {email} sudah dipakai akun lain.')

    account = mm.MerchantAccount(restaurant_id=payload.restaurant_id, name=payload.name,
                                 phone=phone, email=email,
                                 password_hash=hash_password(payload.password),
                                 is_active=payload.is_active, created_by='admin')
    db.add(account)
    db.commit()
    db.refresh(account)
    return _merchant_payload(account)


@router.patch('/merchants/{account_id}/active', response_model=ms.AdminMerchantResponse)
def admin_set_merchant_active(account_id: int, is_active: bool, db: Session = Depends(get_db),
                              _=Depends(_require_admin_key)):
    account = db.query(mm.MerchantAccount).filter(mm.MerchantAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail='Akun merchant tidak ditemukan.')
    account.is_active = bool(is_active)
    if not is_active:
        db.query(mm.MerchantToken).filter(mm.MerchantToken.account_id == account.id).update({'revoked': True})
    db.commit()
    db.refresh(account)
    return _merchant_payload(account)


@router.post('/merchants/{account_id}/password')
def admin_reset_merchant_password(account_id: int, payload: ms.AdminPasswordReset,
                                  db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    account = db.query(mm.MerchantAccount).filter(mm.MerchantAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail='Akun merchant tidak ditemukan.')
    account.password_hash = hash_password(payload.password)
    revoked = db.query(mm.MerchantToken).filter(mm.MerchantToken.account_id == account.id).update({'revoked': True})
    db.commit()
    return {'message': 'Password direset dan semua token lama dicabut.', 'account_id': account.id,
            'tokens_revoked': int(revoked or 0)}


# --------------------------------------------------------------------------- #
# Settlement (kredit saldo hanya setelah approve, idempoten)
# --------------------------------------------------------------------------- #
@router.get('/settlements', response_model=List[ms.AdminSettlementResponse])
def admin_list_settlements(status: Optional[str] = None, db: Session = Depends(get_db),
                           _=Depends(_require_admin_key)):
    q = db.query(mm.MerchantSettlement)
    if status:
        q = q.filter(mm.MerchantSettlement.status == status)
    rows = q.order_by(mm.MerchantSettlement.id.desc()).all()
    return [{**_settlement_payload(s), 'credited': bool(s.ledger_entry_id)} for s in rows]


def _settlement_payload(s: mm.MerchantSettlement) -> dict:
    return {
        'id': s.id, 'order_id': s.order_id, 'restaurant_id': s.restaurant_id,
        'gross_amount': s.gross_amount, 'delivery_fee': s.delivery_fee,
        'platform_fee': s.platform_fee, 'net_amount': s.net_amount, 'status': s.status,
        'note': s.note, 'created_at': s.created_at, 'verified_by': s.verified_by,
        'verified_at': s.verified_at, 'ledger_entry_id': s.ledger_entry_id,
        'credited': bool(s.ledger_entry_id),
    }


@router.post('/settlements', response_model=ms.AdminSettlementResponse, status_code=201)
def admin_create_settlement(payload: ms.AdminSettlementCreate, db: Session = Depends(get_db),
                            _=Depends(_require_admin_key)):
    """Catat settlement sebuah order. Status awal `pending` (belum menambah saldo)."""
    order = db.query(models.Order).filter(models.Order.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail='Pesanan tidak ditemukan.')
    if db.query(mm.MerchantSettlement).filter(mm.MerchantSettlement.order_id == order.id).first():
        raise HTTPException(status_code=409, detail=f'Order #{order.id} sudah punya settlement.')

    gross = int(order.total_price or 0) - int(order.delivery_fee or 0)
    if gross < 0:
        raise HTTPException(status_code=409, detail='Nilai order tidak wajar (ongkir > total).')
    net = gross - int(payload.platform_fee or 0)
    if net < 0:
        raise HTTPException(status_code=422, detail='platform_fee melebihi nilai makanan.')

    row = mm.MerchantSettlement(order_id=order.id, restaurant_id=order.restaurant_id,
                                gross_amount=gross, delivery_fee=int(order.delivery_fee or 0),
                                platform_fee=int(payload.platform_fee or 0), net_amount=net,
                                status='pending', note=payload.note)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _settlement_payload(row)


@router.post('/settlements/{settlement_id}/decision', response_model=ms.AdminSettlementResponse)
def admin_decide_settlement(settlement_id: int, payload: ms.AdminSettlementDecision,
                            db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    """Setujui/tolak settlement. Approve menulis SATU entri ledger (ref unik => idempoten)."""
    row = db.query(mm.MerchantSettlement).filter(mm.MerchantSettlement.id == settlement_id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Settlement tidak ditemukan.')
    if row.status != 'pending':
        raise HTTPException(status_code=409, detail=f'Settlement sudah {row.status}; tidak bisa diubah lagi.')

    if not payload.approve:
        row.status = 'rejected'
        row.note = payload.note or row.note
        row.verified_by = 'admin'
        row.verified_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
        return _settlement_payload(row)

    ref = f'settlement:{row.id}'
    existing = db.query(mm.MerchantLedgerEntry).filter(mm.MerchantLedgerEntry.ref == ref).first()
    if existing:
        row.ledger_entry_id = existing.id
    else:
        entry = mm.MerchantLedgerEntry(restaurant_id=row.restaurant_id, order_id=row.order_id,
                                       kind='settlement', amount=row.net_amount, ref=ref,
                                       note=payload.note or f'Settlement order #{row.order_id}',
                                       created_by='admin')
        db.add(entry)
        db.flush()
        row.ledger_entry_id = entry.id
    row.status = 'approved'
    row.verified_by = 'admin'
    row.verified_at = datetime.utcnow()
    if payload.note:
        row.note = payload.note
    db.commit()
    db.refresh(row)
    return _settlement_payload(row)


# --------------------------------------------------------------------------- #
# Review pencairan (manual; tidak ada payout otomatis)
# --------------------------------------------------------------------------- #
@router.get('/withdrawals', response_model=List[ms.AdminWithdrawalResponse])
def admin_list_withdrawals(status: Optional[str] = None, db: Session = Depends(get_db),
                           _=Depends(_require_admin_key)):
    q = db.query(mm.MerchantWithdrawal)
    if status:
        q = q.filter(mm.MerchantWithdrawal.status == status)
    return q.order_by(mm.MerchantWithdrawal.id.desc()).all()


@router.post('/withdrawals/{withdrawal_id}/review', response_model=ms.AdminWithdrawalResponse)
def admin_review_withdrawal(withdrawal_id: int, payload: ms.AdminWithdrawalReview,
                            db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    """approve = setujui (saldo masih ditahan), reject = tolak, paid = sudah ditransfer manual.

    Saat `paid`, ledger didebit dengan ref unik `withdrawal:{id}` — idempoten.
    """
    row = db.query(mm.MerchantWithdrawal).filter(mm.MerchantWithdrawal.id == withdrawal_id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pengajuan pencairan tidak ditemukan.')

    action = payload.action
    if row.status == 'paid':
        raise HTTPException(status_code=409, detail='Pencairan ini sudah ditandai paid.')
    if action == 'paid' and row.status != 'approved':
        raise HTTPException(status_code=409, detail='Tandai paid hanya untuk pengajuan berstatus approved.')
    if action in ('approve', 'reject') and row.status != 'pending':
        raise HTTPException(status_code=409, detail=f'Pengajuan berstatus {row.status}; tidak bisa di-{action}.')

    if action == 'paid':
        ref = f'withdrawal:{row.id}'
        if not db.query(mm.MerchantLedgerEntry).filter(mm.MerchantLedgerEntry.ref == ref).first():
            entry = mm.MerchantLedgerEntry(restaurant_id=row.restaurant_id, order_id=None,
                                           kind='withdrawal', amount=-int(row.amount), ref=ref,
                                           note=payload.note or f'Pencairan manual #{row.id}',
                                           created_by='admin')
            db.add(entry)
            db.flush()
            row.ledger_entry_id = entry.id
        row.status = 'paid'
    else:
        row.status = 'approved' if action == 'approve' else 'rejected'

    row.reviewed_by = 'admin'
    row.reviewed_at = datetime.utcnow()
    if payload.note:
        row.note = payload.note
    db.commit()
    db.refresh(row)
    return row
