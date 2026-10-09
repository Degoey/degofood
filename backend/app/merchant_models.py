"""Model tabel TAMBAHAN untuk portal merchant DEGOFOOD.

Semua tabel di file ini baru (tidak mengubah skema existing: restaurants, menus,
customers, orders, order_items). Metadata menu/toko diletakkan di tabel terpisah
(merchant_menu_meta / merchant_restaurant_profile) supaya skema lama tetap utuh.

Import modul ini dari app.main sebelum Base.metadata.create_all() dijalankan.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class MerchantAccount(Base):
    """Akun login portal merchant (nomor HP dan/atau email + password)."""

    __tablename__ = 'merchant_accounts'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True, unique=True, index=True)
    email = Column(String, nullable=True, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    restaurant = relationship('Restaurant')

    __table_args__ = (
        UniqueConstraint('restaurant_id', name='uq_merchant_account_restaurant'),
    )


class MerchantToken(Base):
    """Token sesi merchant: yang disimpan hanya SHA-256 dari token acak."""

    __tablename__ = 'merchant_tokens'

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('merchant_accounts.id'), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)


class MerchantAuthEvent(Base):
    """Riwayat percobaan login untuk rate limit (fail closed)."""

    __tablename__ = 'merchant_auth_events'

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, nullable=False, index=True)
    ip = Column(String, nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class MerchantRestaurantProfile(Base):
    """Metadata toko (jam buka, deskripsi) — tabel terpisah dari restaurants."""

    __tablename__ = 'merchant_restaurant_profile'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    open_time = Column(String, nullable=True)          # 'HH:MM'
    close_time = Column(String, nullable=True)         # 'HH:MM'
    min_order = Column(Integer, default=0, nullable=False)
    is_accepting_orders = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MerchantMenuMeta(Base):
    """Metadata menu (kategori, foto URL, stok) — tabel terpisah dari menus."""

    __tablename__ = 'merchant_menu_meta'

    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, ForeignKey('menus.id'), nullable=False, unique=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, index=True)
    category = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    stock = Column(Integer, nullable=True)             # None = stok tak dibatasi
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MerchantPromo(Base):
    """Promo merchant. BELUM diterapkan di checkout pelanggan (lihat catatan API)."""

    __tablename__ = 'merchant_promos'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, index=True)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(String, default='percent', nullable=False)   # percent | amount
    discount_value = Column(Integer, default=0, nullable=False)
    min_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('restaurant_id', 'code', name='uq_merchant_promo_code'),
    )


class MerchantBankAccount(Base):
    """Rekening bank tujuan pencairan (manual, diverifikasi admin)."""

    __tablename__ = 'merchant_bank_accounts'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, index=True)
    bank_name = Column(String, nullable=False)
    account_no = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MerchantLedgerEntry(Base):
    """Buku besar saldo merchant. Amount bertanda: + kredit, - debit.

    `ref` unik => penulisan ledger idempoten (tidak ada kredit ganda).
    """

    __tablename__ = 'merchant_ledger'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, index=True)
    order_id = Column(Integer, nullable=True, index=True)
    kind = Column(String, nullable=False)              # settlement | withdrawal | adjustment
    amount = Column(Integer, nullable=False)
    ref = Column(String, nullable=False, unique=True, index=True)
    note = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MerchantSettlement(Base):
    """Penyelesaian pembayaran per order; dibuat & diverifikasi ADMIN.

    Order hanya dikreditkan ke ledger setelah admin menyetujui (bukan otomatis).
    """

    __tablename__ = 'merchant_settlements'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, unique=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, index=True)
    gross_amount = Column(Integer, nullable=False)
    delivery_fee = Column(Integer, default=0, nullable=False)
    platform_fee = Column(Integer, default=0, nullable=False)
    net_amount = Column(Integer, nullable=False)
    status = Column(String, default='pending', nullable=False)   # pending | approved | rejected
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    ledger_entry_id = Column(Integer, nullable=True)


class MerchantWithdrawal(Base):
    """Pengajuan pencairan manual. Tidak ada payout otomatis."""

    __tablename__ = 'merchant_withdrawals'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    bank_name = Column(String, nullable=False)
    account_no = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    status = Column(String, default='pending', nullable=False)   # pending | approved | rejected | paid
    client_ref = Column(String, nullable=True, unique=True, index=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    ledger_entry_id = Column(Integer, nullable=True)


class MerchantRegistration(Base):
    """Pendaftaran mandiri calon merchant (BELUM punya akses apa pun).

    Baris di sini hanya sebuah PERMOHONAN. Akun di `merchant_accounts` baru dibuat
    saat admin menyetujui (approve) sekaligus menautkan restoran. Selama status
    masih `pending`, login ditolak dan tidak ada data/order yang bisa diakses.

    Restoran TIDAK PERNAH diklaim otomatis dari nomor HP: admin yang menentukan
    restoran mana yang ditautkan (atau membuat restoran baru).
    """

    __tablename__ = 'merchant_registrations'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    password_hash = Column(String, nullable=False)
    store_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    note = Column(String, nullable=True)
    status = Column(String, default='pending', nullable=False, index=True)  # pending|approved|rejected
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=True)
    account_id = Column(Integer, ForeignKey('merchant_accounts.id'), nullable=True)
    ip = Column(String, nullable=True, index=True)
    review_note = Column(String, nullable=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class MerchantOrderEvent(Base):
    """Jejak perubahan status order oleh merchant."""

    __tablename__ = 'merchant_order_events'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, index=True)
    restaurant_id = Column(Integer, nullable=False, index=True)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    actor = Column(String, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
