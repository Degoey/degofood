"""Router portal merchant DEGOFOOD (/api/merchant/*).

Semua endpoint (kecuali auth/login) WAJIB Bearer token merchant dan hanya boleh
mengakses data restoran milik akun tersebut (token ownership).

Catatan jujur:
- Promo disimpan sebagai data; belum diterapkan otomatis di checkout pelanggan.
- Saldo hanya bertambah setelah admin memverifikasi settlement per order
  (tidak ada kredit histori otomatis, tidak ada payout otomatis).
- Notifikasi = polling saat aplikasi terbuka, bukan push background.
"""

import csv
import io
import os
import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from .. import merchant_models as mm
from .. import merchant_schemas as ms
from .. import models
from ..merchant_security import (
    get_current_account,
    hash_password,
    issue_token,
    login_blocked,
    owned_restaurant_id,
    password_policy_error,
    record_login_attempt,
    registration_rate_limit,
    revoke_token,
    verify_password,
)

router = APIRouter()

# --------------------------------------------------------------------------- #
# Status pesanan
# --------------------------------------------------------------------------- #
PENDING_STATUSES = ('Menunggu Konfirmasi', 'Dikonfirmasi', 'Sedang Dimasak', 'Sedang Diantar')
TRANSITIONS = {
    'Menunggu Konfirmasi': ['Dikonfirmasi', 'Dibatalkan'],
    'Dikonfirmasi': ['Sedang Dimasak', 'Dibatalkan'],
    'Sedang Dimasak': ['Sedang Diantar', 'Dibatalkan'],
    'Sedang Diantar': ['Selesai'],
    'Selesai': [],
    'Dibatalkan': [],
}
ACTIVE_STATUSES = ('Menunggu Konfirmasi', 'Dikonfirmasi', 'Sedang Dimasak', 'Sedang Diantar')

_wd_lock = threading.Lock()   # serialisasi pengajuan withdrawal dalam 1 proses


def _norm_phone(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r'[^0-9]', '', raw)
    if digits.startswith('62'):
        digits = digits[2:]
    elif digits.startswith('0'):
        digits = digits[1:]
    return '+62' + digits if digits else None


def _norm_email(raw: Optional[str]) -> Optional[str]:
    value = (raw or '').strip().lower()
    return value or None


def _is_email(identifier: str) -> bool:
    return '@' in (identifier or '')


_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$')


def _valid_email(value: Optional[str]) -> bool:
    return bool(_EMAIL_RE.match((value or '').strip()))


def _find_registration(db: Session, identifier: str) -> Optional[mm.MerchantRegistration]:
    """Pendaftaran terakhir untuk identifier yang sama (dipakai saat login pending)."""
    q = db.query(mm.MerchantRegistration)
    if _is_email(identifier):
        return q.filter(mm.MerchantRegistration.email == _norm_email(identifier)) \
            .order_by(mm.MerchantRegistration.id.desc()).first()
    phone = _norm_phone(identifier)
    if not phone:
        return None
    return q.filter(mm.MerchantRegistration.phone == phone) \
        .order_by(mm.MerchantRegistration.id.desc()).first()


def _parse_date(value: Optional[str], end: bool = False) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.strptime(value.strip()[:10], '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=422, detail='Format tanggal harus YYYY-MM-DD.')
    return dt + (timedelta(days=1) if end else timedelta(0))


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@router.post('/auth/login', response_model=ms.MerchantLoginResponse)
def merchant_login(payload: ms.MerchantLoginRequest, request: Request, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    norm_id = (_norm_phone(identifier) or '') if not _is_email(identifier) else _norm_email(identifier)
    ip = request.client.host if request.client else None

    if login_blocked(db, norm_id, ip):
        raise HTTPException(status_code=429,
                            detail='Terlalu banyak percobaan login gagal. Coba lagi nanti.')

    q = db.query(mm.MerchantAccount)
    if _is_email(identifier):
        account = q.filter(mm.MerchantAccount.email == _norm_email(identifier)).first()
    else:
        account = q.filter(mm.MerchantAccount.phone == norm_id).first()

    if not account or not verify_password(payload.password, account.password_hash):
        record_login_attempt(db, norm_id, ip, success=False)
        if not account:
            reg = _find_registration(db, identifier)
            if reg and reg.status == 'pending':
                raise HTTPException(
                    status_code=403,
                    detail='Pendaftaran Anda masih MENUNGGU VERIFIKASI admin DEGOFOOD. '
                           'Akun belum aktif dan belum bisa mengakses data/order.')
            if reg and reg.status == 'rejected':
                raise HTTPException(
                    status_code=403,
                    detail='Pendaftaran Anda ditolak admin. '
                           + (reg.review_note or 'Hubungi admin DEGOFOOD untuk info lebih lanjut.'))
        raise HTTPException(status_code=401, detail='Nomor HP/email atau password salah.')
    if not account.is_active:
        record_login_attempt(db, norm_id, ip, success=False)
        raise HTTPException(status_code=403, detail='Akun merchant dinonaktifkan admin.')

    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == account.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=409, detail='Restoran akun ini tidak ditemukan.')

    raw_token, expires_at = issue_token(db, account, label=request.headers.get('user-agent'))
    record_login_attempt(db, norm_id, ip, success=True)

    return {
        'token': raw_token,
        'expires_at': expires_at,
        'account': {
            'id': account.id,
            'name': account.name,
            'phone': account.phone,
            'email': account.email,
            'restaurant_id': account.restaurant_id,
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.name,
                'address': restaurant.address,
                'phone': restaurant.phone,
                'is_open': restaurant.is_open,
            },
        },
    }


@router.post('/auth/register', response_model=ms.MerchantRegisterResponse, status_code=201)
def merchant_register(payload: ms.MerchantRegisterRequest, request: Request,
                      db: Session = Depends(get_db)):
    """Pendaftaran mandiri merchant: nomor HP ATAU email + password pilihannya sendiri.

    Akun TIDAK langsung aktif. Baris masuk sebagai `pending`; admin harus approve
    DAN menautkan restoran sebelum login diizinkan. Nomor HP tidak pernah dipakai
    untuk mengklaim restoran secara otomatis.
    """
    ip = request.client.host if request.client else None
    phone = _norm_phone(payload.phone)
    email = _norm_email(payload.email)

    if not phone and not email:
        raise HTTPException(status_code=422, detail='Isi nomor HP atau email (minimal salah satu).')
    if phone and len(phone) < 11:
        raise HTTPException(status_code=422, detail='Nomor HP tidak valid (contoh: 08123456789).')
    if email and not _valid_email(email):
        raise HTTPException(status_code=422, detail='Format email tidak valid.')

    policy_error = password_policy_error(payload.password)
    if policy_error:
        raise HTTPException(status_code=422, detail=policy_error)

    blocked = registration_rate_limit(db, ip)
    if blocked:
        raise HTTPException(status_code=429, detail=blocked)

    if phone and db.query(mm.MerchantAccount).filter(mm.MerchantAccount.phone == phone).first():
        raise HTTPException(status_code=409,
                            detail='Nomor HP ini sudah terdaftar. Silakan masuk atau hubungi admin.')
    if email and db.query(mm.MerchantAccount).filter(mm.MerchantAccount.email == email).first():
        raise HTTPException(status_code=409,
                            detail='Email ini sudah terdaftar. Silakan masuk atau hubungi admin.')

    conds = []
    if phone:
        conds.append(mm.MerchantRegistration.phone == phone)
    if email:
        conds.append(mm.MerchantRegistration.email == email)
    duplicate = db.query(mm.MerchantRegistration).filter(
        mm.MerchantRegistration.status == 'pending', or_(*conds)).first()
    if duplicate:
        raise HTTPException(status_code=409,
                            detail='Pendaftaran dengan nomor HP/email ini sudah ada dan masih '
                                   'menunggu verifikasi admin.')

    row = mm.MerchantRegistration(
        name=payload.name.strip(),
        phone=phone,
        email=email,
        password_hash=hash_password(payload.password),
        store_name=(payload.store_name or '').strip() or None,
        address=(payload.address or '').strip() or None,
        status='pending',
        ip=ip,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {'id': row.id, 'status': row.status, 'name': row.name, 'phone': row.phone,
            'email': row.email, 'store_name': row.store_name, 'created_at': row.created_at}


@router.post('/auth/logout')
def merchant_logout(authorization: Optional[str] = Header(default=None),
                    db: Session = Depends(get_db),
                    account: mm.MerchantAccount = Depends(get_current_account)):
    raw = (authorization or '').split(None, 1)[-1].strip()
    revoke_token(db, raw)
    return {'message': 'Token merchant dicabut.'}


@router.get('/me', response_model=ms.MerchantAccountInfo)
def merchant_me(db: Session = Depends(get_db), account: mm.MerchantAccount = Depends(get_current_account)):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == account.restaurant_id).first()
    return {
        'id': account.id,
        'name': account.name,
        'phone': account.phone,
        'email': account.email,
        'restaurant_id': account.restaurant_id,
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
            'address': restaurant.address,
            'phone': restaurant.phone,
            'is_open': restaurant.is_open,
        },
    }


# --------------------------------------------------------------------------- #
# Helper keuangan
# --------------------------------------------------------------------------- #
def _ledger_total(db: Session, restaurant_id: int) -> int:
    total = db.query(func.coalesce(func.sum(mm.MerchantLedgerEntry.amount), 0)).filter(
        mm.MerchantLedgerEntry.restaurant_id == restaurant_id).scalar()
    return int(total or 0)


def _reserved_total(db: Session, restaurant_id: int) -> int:
    total = db.query(func.coalesce(func.sum(mm.MerchantWithdrawal.amount), 0)).filter(
        mm.MerchantWithdrawal.restaurant_id == restaurant_id,
        mm.MerchantWithdrawal.status.in_(['pending', 'approved']),
    ).scalar()
    return int(total or 0)


def _balance(db: Session, restaurant_id: int) -> dict:
    ledger = _ledger_total(db, restaurant_id)
    reserved = _reserved_total(db, restaurant_id)
    pending_settle = db.query(func.count(mm.MerchantSettlement.id)).filter(
        mm.MerchantSettlement.restaurant_id == restaurant_id,
        mm.MerchantSettlement.status == 'pending').scalar()
    approved_settle = db.query(func.count(mm.MerchantSettlement.id)).filter(
        mm.MerchantSettlement.restaurant_id == restaurant_id,
        mm.MerchantSettlement.status == 'approved').scalar()
    return {
        'restaurant_id': restaurant_id,
        'ledger_total': ledger,
        'pending_withdrawal_total': reserved,
        'available_balance': max(ledger - reserved, 0),
        'settlements_pending': int(pending_settle or 0),
        'settlements_approved': int(approved_settle or 0),
    }


def _menu_meta_map(db: Session, restaurant_id: int) -> dict:
    rows = db.query(mm.MerchantMenuMeta).filter(mm.MerchantMenuMeta.restaurant_id == restaurant_id).all()
    return {r.menu_id: r for r in rows}


def _menu_payload(menu: models.Menu, meta: Optional[mm.MerchantMenuMeta]) -> dict:
    return {
        'id': menu.id,
        'restaurant_id': menu.restaurant_id,
        'name': menu.name,
        'description': menu.description,
        'price': menu.price,
        'is_available': menu.is_available,
        'category': getattr(meta, 'category', None),
        'image_url': getattr(meta, 'image_url', None),
        'stock': getattr(meta, 'stock', None),
    }


def _order_payload(db: Session, order: models.Order) -> dict:
    customer = db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
    return {
        'id': order.id,
        'customer_id': order.customer_id,
        'customer_name': customer.name if customer else None,
        'customer_phone': customer.phone if customer else None,
        'total_price': order.total_price,
        'delivery_fee': order.delivery_fee,
        'status': order.status,
        'delivery_address': order.delivery_address,
        'notes': order.notes,
        'driver_name': order.driver_name,
        'created_at': order.created_at,
        'items': [
            {'id': i.id, 'menu_id': i.menu_id, 'menu_name': i.menu_name,
             'quantity': i.quantity, 'price': i.price}
            for i in order.items
        ],
        'allowed_next_status': TRANSITIONS.get(order.status, []),
    }


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@router.get('/dashboard')
def merchant_dashboard(db: Session = Depends(get_db), account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    base = db.query(models.Order).filter(models.Order.restaurant_id == rid)
    today_orders = base.filter(models.Order.created_at >= today).all()
    today_revenue = sum(o.total_price - o.delivery_fee for o in today_orders if o.status != 'Dibatalkan')

    pending = base.filter(models.Order.status.in_(ACTIVE_STATUSES)).count()
    total_orders = base.count()
    active_menus = db.query(models.Menu).filter(models.Menu.restaurant_id == rid,
                                               models.Menu.is_available == True).count()  # noqa: E712

    series = []
    for offset in range(6, -1, -1):
        day_start = today - timedelta(days=offset)
        day_end = day_start + timedelta(days=1)
        day_orders = base.filter(models.Order.created_at >= day_start,
                                 models.Order.created_at < day_end).all()
        series.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'orders': len(day_orders),
            'revenue': sum(o.total_price - o.delivery_fee for o in day_orders if o.status != 'Dibatalkan'),
        })

    top_rows = db.query(models.OrderItem.menu_name,
                        func.sum(models.OrderItem.quantity),
                        func.sum(models.OrderItem.quantity * models.OrderItem.price)).join(
        models.Order, models.Order.id == models.OrderItem.order_id).filter(
        models.Order.restaurant_id == rid,
        models.Order.created_at >= today - timedelta(days=30),
    ).group_by(models.OrderItem.menu_name).order_by(func.sum(models.OrderItem.quantity).desc()).limit(5).all()

    return {
        'restaurant': {
            'id': rid,
            'name': account.restaurant.name if account.restaurant else None,
            'is_open': bool(account.restaurant.is_open) if account.restaurant else False,
        },
        'stats': {
            'today_orders': len(today_orders),
            'today_revenue': today_revenue,
            'active_orders': pending,
            'total_orders': total_orders,
            'active_menus': int(active_menus or 0),
            'avg_order_value': int(sum(o.total_price for o in today_orders) / len(today_orders)) if today_orders else 0,
        },
        'series': series,
        'top_menus': [{'name': r[0], 'quantity': int(r[1] or 0), 'revenue': int(r[2] or 0)} for r in top_rows],
        'balance': _balance(db, rid),
        'notifications_mode': 'foreground_polling',
    }


# --------------------------------------------------------------------------- #
# Pesanan
# --------------------------------------------------------------------------- #
@router.get('/orders', response_model=List[ms.MerchantOrderResponse])
def merchant_orders(status: Optional[str] = None,
                    date_from: Optional[str] = None,
                    date_to: Optional[str] = None,
                    limit: int = Query(default=100, ge=1, le=500),
                    db: Session = Depends(get_db),
                    account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    q = db.query(models.Order).filter(models.Order.restaurant_id == rid)
    if status == 'aktif':
        q = q.filter(models.Order.status.in_(ACTIVE_STATUSES))
    elif status:
        q = q.filter(models.Order.status == status)
    start, end = _parse_date(date_from), _parse_date(date_to, end=True)
    if start:
        q = q.filter(models.Order.created_at >= start)
    if end:
        q = q.filter(models.Order.created_at < end)
    orders = q.order_by(models.Order.created_at.desc()).limit(limit).all()
    return [_order_payload(db, o) for o in orders]


@router.get('/orders/{order_id}', response_model=ms.MerchantOrderResponse)
def merchant_order_detail(order_id: int, db: Session = Depends(get_db),
                          account: mm.MerchantAccount = Depends(get_current_account)):
    from ..merchant_security import get_owned_order
    return _order_payload(db, get_owned_order(db, account, order_id))


@router.post('/orders/{order_id}/status', response_model=ms.MerchantOrderResponse)
def merchant_update_order_status(order_id: int, payload: ms.MerchantOrderStatusUpdate,
                                 db: Session = Depends(get_db),
                                 account: mm.MerchantAccount = Depends(get_current_account)):
    from ..merchant_security import get_owned_order
    order = get_owned_order(db, account, order_id)
    target = payload.status.strip()
    allowed = TRANSITIONS.get(order.status, [])
    if target not in allowed:
        raise HTTPException(status_code=409,
                            detail=f'Transisi status {order.status!r} -> {target!r} tidak diizinkan. '
                                   f'Pilihan: {allowed or "tidak ada (status final)"}.')
    db.add(mm.MerchantOrderEvent(order_id=order.id, restaurant_id=order.restaurant_id,
                                 from_status=order.status, to_status=target,
                                 actor=f'merchant:{account.id}', note=payload.note))
    order.status = target
    db.commit()
    db.refresh(order)
    return _order_payload(db, order)


@router.get('/orders/{order_id}/events', response_model=List[ms.MerchantOrderEventResponse])
def merchant_order_events(order_id: int, db: Session = Depends(get_db),
                          account: mm.MerchantAccount = Depends(get_current_account)):
    from ..merchant_security import get_owned_order
    order = get_owned_order(db, account, order_id)
    return db.query(mm.MerchantOrderEvent).filter(
        mm.MerchantOrderEvent.order_id == order.id).order_by(mm.MerchantOrderEvent.id).all()


# --------------------------------------------------------------------------- #
# Menu (CRUD) + metadata di tabel terpisah
# --------------------------------------------------------------------------- #
@router.get('/menus', response_model=List[ms.MerchantMenuResponse])
def merchant_menus(category: Optional[str] = None,
                   q: Optional[str] = None,
                   db: Session = Depends(get_db),
                   account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    menus = db.query(models.Menu).filter(models.Menu.restaurant_id == rid).order_by(models.Menu.id).all()
    meta_map = _menu_meta_map(db, rid)
    payload = [_menu_payload(m, meta_map.get(m.id)) for m in menus]
    if category:
        payload = [p for p in payload if (p.get('category') or '') == category]
    if q:
        needle = q.lower()
        payload = [p for p in payload if needle in (p['name'] or '').lower()
                   or needle in (p.get('description') or '').lower()]
    return payload


@router.get('/menu-categories')
def merchant_menu_categories(db: Session = Depends(get_db),
                             account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    rows = db.query(mm.MerchantMenuMeta.category).filter(
        mm.MerchantMenuMeta.restaurant_id == rid,
        mm.MerchantMenuMeta.category.isnot(None)).distinct().all()
    return {'categories': sorted({r[0] for r in rows if r[0]})}


@router.post('/menus', response_model=ms.MerchantMenuResponse)
def merchant_create_menu(payload: ms.MerchantMenuUpsert, db: Session = Depends(get_db),
                         account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    menu = models.Menu(restaurant_id=rid, name=payload.name, description=payload.description,
                       price=payload.price, is_available=payload.is_available)
    db.add(menu)
    db.flush()
    if payload.category or payload.image_url or payload.stock is not None:
        db.add(mm.MerchantMenuMeta(menu_id=menu.id, restaurant_id=rid, category=payload.category,
                                   image_url=payload.image_url, stock=payload.stock))
    db.commit()
    db.refresh(menu)
    meta = db.query(mm.MerchantMenuMeta).filter(mm.MerchantMenuMeta.menu_id == menu.id).first()
    return _menu_payload(menu, meta)


@router.put('/menus/{menu_id}', response_model=ms.MerchantMenuResponse)
def merchant_update_menu(menu_id: int, payload: ms.MerchantMenuUpsert, db: Session = Depends(get_db),
                         account: mm.MerchantAccount = Depends(get_current_account)):
    from ..merchant_security import get_owned_menu
    rid = owned_restaurant_id(account)
    menu = get_owned_menu(db, account, menu_id)
    menu.name = payload.name
    menu.description = payload.description
    menu.price = payload.price
    menu.is_available = payload.is_available
    meta = db.query(mm.MerchantMenuMeta).filter(mm.MerchantMenuMeta.menu_id == menu.id).first()
    if not meta:
        meta = mm.MerchantMenuMeta(menu_id=menu.id, restaurant_id=rid)
        db.add(meta)
    meta.category = payload.category
    meta.image_url = payload.image_url
    meta.stock = payload.stock
    db.commit()
    db.refresh(menu)
    return _menu_payload(menu, meta)


@router.delete('/menus/{menu_id}')
def merchant_delete_menu(menu_id: int, db: Session = Depends(get_db),
                         account: mm.MerchantAccount = Depends(get_current_account)):
    from ..merchant_security import get_owned_menu
    menu = get_owned_menu(db, account, menu_id)
    db.query(mm.MerchantMenuMeta).filter(mm.MerchantMenuMeta.menu_id == menu.id).delete()
    db.delete(menu)
    db.commit()
    return {'message': 'Menu dihapus.', 'menu_id': menu_id}


# --------------------------------------------------------------------------- #
# Profil toko (jam buka) — metadata di tabel terpisah
# --------------------------------------------------------------------------- #
def _profile_payload(db: Session, account: mm.MerchantAccount) -> dict:
    rid = owned_restaurant_id(account)
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == rid).first()
    profile = db.query(mm.MerchantRestaurantProfile).filter(
        mm.MerchantRestaurantProfile.restaurant_id == rid).first()
    return {
        'restaurant_id': rid,
        'name': restaurant.name,
        'address': restaurant.address,
        'phone': restaurant.phone,
        'is_open': bool(restaurant.is_open),
        'description': getattr(profile, 'description', None),
        'open_time': getattr(profile, 'open_time', None),
        'close_time': getattr(profile, 'close_time', None),
        'min_order': int(getattr(profile, 'min_order', 0) or 0),
        'is_accepting_orders': bool(getattr(profile, 'is_accepting_orders', True)),
    }


@router.get('/profile', response_model=ms.MerchantProfileResponse)
def merchant_get_profile(db: Session = Depends(get_db),
                         account: mm.MerchantAccount = Depends(get_current_account)):
    return _profile_payload(db, account)


@router.put('/profile', response_model=ms.MerchantProfileResponse)
def merchant_update_profile(payload: ms.MerchantProfileUpdate, db: Session = Depends(get_db),
                            account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == rid).first()
    profile = db.query(mm.MerchantRestaurantProfile).filter(
        mm.MerchantRestaurantProfile.restaurant_id == rid).first()
    if not profile:
        profile = mm.MerchantRestaurantProfile(restaurant_id=rid)
        db.add(profile)
    data = payload.model_dump(exclude_unset=True)
    for field in ('description', 'open_time', 'close_time', 'min_order', 'is_accepting_orders'):
        if field in data and data[field] is not None:
            setattr(profile, field, data[field])
    if data.get('is_open') is not None:
        restaurant.is_open = bool(data['is_open'])
    db.commit()
    return _profile_payload(db, account)


# --------------------------------------------------------------------------- #
# Promo (CRUD; belum diterapkan di checkout)
# --------------------------------------------------------------------------- #
PROMO_NOTE = ('Promo tersimpan dan bisa dikelola merchant, tetapi BELUM diterapkan otomatis '
              'saat checkout pelanggan (butuh perubahan pada backend order).')


def _promo_payload(promo: mm.MerchantPromo) -> dict:
    return {
        'id': promo.id, 'restaurant_id': promo.restaurant_id, 'code': promo.code,
        'title': promo.title, 'description': promo.description,
        'discount_type': promo.discount_type, 'discount_value': promo.discount_value,
        'min_order': promo.min_order, 'is_active': promo.is_active,
        'starts_at': promo.starts_at, 'ends_at': promo.ends_at, 'created_at': promo.created_at,
        'applied_at_checkout': False, 'note': PROMO_NOTE,
    }


@router.get('/promos', response_model=List[ms.MerchantPromoResponse])
def merchant_promos(db: Session = Depends(get_db),
                    account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    rows = db.query(mm.MerchantPromo).filter(mm.MerchantPromo.restaurant_id == rid
                                             ).order_by(mm.MerchantPromo.id.desc()).all()
    return [_promo_payload(p) for p in rows]


@router.post('/promos', response_model=ms.MerchantPromoResponse)
def merchant_create_promo(payload: ms.MerchantPromoUpsert, db: Session = Depends(get_db),
                          account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    code = payload.code.strip().upper()
    exists = db.query(mm.MerchantPromo).filter(mm.MerchantPromo.restaurant_id == rid,
                                               mm.MerchantPromo.code == code).first()
    if exists:
        raise HTTPException(status_code=409, detail=f'Kode promo {code} sudah dipakai.')
    promo = mm.MerchantPromo(restaurant_id=rid, **{**payload.model_dump(), 'code': code})
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return _promo_payload(promo)


@router.put('/promos/{promo_id}', response_model=ms.MerchantPromoResponse)
def merchant_update_promo(promo_id: int, payload: ms.MerchantPromoUpsert, db: Session = Depends(get_db),
                          account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    promo = db.query(mm.MerchantPromo).filter(mm.MerchantPromo.id == promo_id,
                                              mm.MerchantPromo.restaurant_id == rid).first()
    if not promo:
        raise HTTPException(status_code=404, detail='Promo tidak ditemukan untuk restoran Anda.')
    data = payload.model_dump()
    data['code'] = data['code'].strip().upper()
    for key, value in data.items():
        setattr(promo, key, value)
    db.commit()
    db.refresh(promo)
    return _promo_payload(promo)


@router.delete('/promos/{promo_id}')
def merchant_delete_promo(promo_id: int, db: Session = Depends(get_db),
                          account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    promo = db.query(mm.MerchantPromo).filter(mm.MerchantPromo.id == promo_id,
                                              mm.MerchantPromo.restaurant_id == rid).first()
    if not promo:
        raise HTTPException(status_code=404, detail='Promo tidak ditemukan untuk restoran Anda.')
    db.delete(promo)
    db.commit()
    return {'message': 'Promo dihapus.', 'promo_id': promo_id}


# --------------------------------------------------------------------------- #
# Keuangan: saldo, ledger, rekening bank, pencairan, laporan CSV
# --------------------------------------------------------------------------- #
@router.get('/finance/summary', response_model=ms.MerchantBalanceResponse)
def merchant_finance_summary(db: Session = Depends(get_db),
                             account: mm.MerchantAccount = Depends(get_current_account)):
    return _balance(db, owned_restaurant_id(account))


@router.get('/finance/ledger', response_model=List[ms.MerchantLedgerEntryResponse])
def merchant_ledger(limit: int = Query(default=100, ge=1, le=500),
                    db: Session = Depends(get_db),
                    account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    return db.query(mm.MerchantLedgerEntry).filter(
        mm.MerchantLedgerEntry.restaurant_id == rid
    ).order_by(mm.MerchantLedgerEntry.id.desc()).limit(limit).all()


@router.get('/finance/report.csv')
def merchant_report_csv(date_from: Optional[str] = None, date_to: Optional[str] = None,
                        db: Session = Depends(get_db),
                        account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    q = db.query(models.Order).filter(models.Order.restaurant_id == rid)
    start, end = _parse_date(date_from), _parse_date(date_to, end=True)
    if start:
        q = q.filter(models.Order.created_at >= start)
    if end:
        q = q.filter(models.Order.created_at < end)
    orders = q.order_by(models.Order.created_at).all()

    settlements = {s.order_id: s for s in db.query(mm.MerchantSettlement).filter(
        mm.MerchantSettlement.restaurant_id == rid).all()}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['order_id', 'tanggal', 'pelanggan', 'alamat', 'item', 'subtotal',
                     'ongkir', 'total', 'status', 'status_settlement'])
    for o in orders:
        customer = db.query(models.Customer).filter(models.Customer.id == o.customer_id).first()
        items = '; '.join(f'{i.menu_name} x{i.quantity}' for i in o.items)
        st = settlements.get(o.id)
        writer.writerow([o.id, o.created_at.strftime('%Y-%m-%d %H:%M'), customer.name if customer else '',
                         o.delivery_address, items, o.total_price - o.delivery_fee,
                         o.delivery_fee, o.total_price, o.status, st.status if st else 'belum'])

    stamp = datetime.utcnow().strftime('%Y%m%d')
    return Response(content=buf.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="laporan-{rid}-{stamp}.csv"'})


@router.get('/bank-accounts', response_model=List[ms.MerchantBankAccountResponse])
def merchant_bank_accounts(db: Session = Depends(get_db),
                           account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    return db.query(mm.MerchantBankAccount).filter(
        mm.MerchantBankAccount.restaurant_id == rid).order_by(mm.MerchantBankAccount.id).all()


@router.post('/bank-accounts', response_model=ms.MerchantBankAccountResponse)
def merchant_add_bank_account(payload: ms.MerchantBankAccountUpsert, db: Session = Depends(get_db),
                              account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    if payload.is_primary:
        db.query(mm.MerchantBankAccount).filter(mm.MerchantBankAccount.restaurant_id == rid).update(
            {'is_primary': False})
    row = mm.MerchantBankAccount(restaurant_id=rid, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete('/bank-accounts/{account_id}')
def merchant_delete_bank_account(account_id: int, db: Session = Depends(get_db),
                                 account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    row = db.query(mm.MerchantBankAccount).filter(mm.MerchantBankAccount.id == account_id,
                                                  mm.MerchantBankAccount.restaurant_id == rid).first()
    if not row:
        raise HTTPException(status_code=404, detail='Rekening tidak ditemukan untuk restoran Anda.')
    db.delete(row)
    db.commit()
    return {'message': 'Rekening dihapus.', 'id': account_id}


@router.get('/withdrawals', response_model=List[ms.MerchantWithdrawalResponse])
def merchant_withdrawals(db: Session = Depends(get_db),
                         account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    return db.query(mm.MerchantWithdrawal).filter(
        mm.MerchantWithdrawal.restaurant_id == rid).order_by(mm.MerchantWithdrawal.id.desc()).all()


@router.post('/withdrawals', response_model=ms.MerchantWithdrawalResponse)
def merchant_create_withdrawal(payload: ms.MerchantWithdrawalCreate, db: Session = Depends(get_db),
                               account: mm.MerchantAccount = Depends(get_current_account)):
    """Pengajuan pencairan manual.

    - Idempoten terhadap `client_ref` (kirim ulang ref sama => baris sama, tidak dobel).
    - Saldo dicek ulang di dalam transaksi (ledger - withdrawal pending/approved),
      jadi pengajuan kedua yang melebihi saldo tersedia ditolak (tidak double spend).
    - Uang TIDAK dikirim otomatis; admin harus mereview (approve/reject/paid).
    """
    rid = owned_restaurant_id(account)

    if payload.client_ref:
        existing = db.query(mm.MerchantWithdrawal).filter(
            mm.MerchantWithdrawal.client_ref == payload.client_ref).first()
        if existing:
            if existing.restaurant_id != rid:
                raise HTTPException(status_code=409, detail='client_ref sudah dipakai restoran lain.')
            return existing

    bank = None
    if payload.bank_account_id:
        bank = db.query(mm.MerchantBankAccount).filter(
            mm.MerchantBankAccount.id == payload.bank_account_id,
            mm.MerchantBankAccount.restaurant_id == rid).first()
        if not bank:
            raise HTTPException(status_code=404, detail='Rekening bank tidak ditemukan untuk restoran Anda.')
    bank_name = payload.bank_name or (bank.bank_name if bank else None)
    account_no = payload.account_no or (bank.account_no if bank else None)
    account_name = payload.account_name or (bank.account_name if bank else None)
    if not (bank_name and account_no and account_name):
        raise HTTPException(status_code=422,
                            detail='Isi bank_account_id atau bank_name/account_no/account_name.')

    with _wd_lock:
        balance = _balance(db, rid)
        if payload.amount > balance['available_balance']:
            raise HTTPException(
                status_code=400,
                detail=f'Saldo tersedia Rp {balance["available_balance"]:,} lebih kecil dari '
                       f'pengajuan Rp {payload.amount:,}. Saldo hanya bertambah setelah admin '
                       f'memverifikasi settlement order.'.replace(',', '.'))
        row = mm.MerchantWithdrawal(restaurant_id=rid, amount=payload.amount, bank_name=bank_name,
                                    account_no=account_no, account_name=account_name,
                                    status='pending', client_ref=payload.client_ref)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


# --------------------------------------------------------------------------- #
# Notifikasi (foreground polling)
# --------------------------------------------------------------------------- #
@router.get('/notifications', response_model=ms.MerchantNotificationFeed)
def merchant_notifications(since_order_id: int = Query(default=0, ge=0),
                           since_event_id: int = Query(default=0, ge=0),
                           db: Session = Depends(get_db),
                           account: mm.MerchantAccount = Depends(get_current_account)):
    rid = owned_restaurant_id(account)
    items = []

    new_orders = db.query(models.Order).filter(
        models.Order.restaurant_id == rid, models.Order.id > since_order_id
    ).order_by(models.Order.id).limit(20).all()
    for o in new_orders:
        items.append({'id': f'order:{o.id}', 'kind': 'new_order', 'order_id': o.id,
                      'title': f'Pesanan baru #{o.id}',
                      'body': f'{len(o.items)} item • Rp {o.total_price:,}'.replace(',', '.'),
                      'created_at': o.created_at})

    events = db.query(mm.MerchantOrderEvent).filter(
        mm.MerchantOrderEvent.restaurant_id == rid, mm.MerchantOrderEvent.id > since_event_id
    ).order_by(mm.MerchantOrderEvent.id).limit(20).all()
    for ev in events:
        items.append({'id': f'event:{ev.id}', 'kind': 'status_change', 'order_id': ev.order_id,
                      'title': f'Pesanan #{ev.order_id} → {ev.to_status}',
                      'body': f'Dari {ev.from_status or "-"} ke {ev.to_status}',
                      'created_at': ev.created_at})

    return {
        'new_order_cursor': max([o.id for o in new_orders], default=since_order_id),
        'event_cursor': max([e.id for e in events], default=since_event_id),
        'items': items,
    }
