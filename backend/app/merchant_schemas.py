"""Skema Pydantic untuk portal merchant DEGOFOOD."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class MerchantLoginRequest(BaseModel):
    identifier: str = Field(min_length=4, max_length=120,
                            description='Nomor HP (08xx/+62xx) atau email terdaftar')
    password: str = Field(min_length=8, max_length=200)


class MerchantRestaurantInfo(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    is_open: bool = True


class MerchantAccountInfo(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    restaurant_id: int
    restaurant: MerchantRestaurantInfo


class MerchantLoginResponse(BaseModel):
    token: str
    token_type: str = 'Bearer'
    expires_at: datetime
    account: MerchantAccountInfo


# --------------------------------------------------------------------------- #
# Profil toko
# --------------------------------------------------------------------------- #
class MerchantProfileUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=1000)
    open_time: Optional[str] = Field(default=None, max_length=5)
    close_time: Optional[str] = Field(default=None, max_length=5)
    min_order: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    is_accepting_orders: Optional[bool] = None
    is_open: Optional[bool] = None          # ditulis ke tabel restaurants (kolom existing)


class MerchantProfileResponse(BaseModel):
    restaurant_id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    is_open: bool = True
    description: Optional[str] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    min_order: int = 0
    is_accepting_orders: bool = True


# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #
class MerchantMenuUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    price: int = Field(ge=0, le=100_000_000)
    is_available: bool = True
    category: Optional[str] = Field(default=None, max_length=60)
    image_url: Optional[str] = Field(default=None, max_length=500)
    stock: Optional[int] = Field(default=None, ge=0, le=1_000_000)


class MerchantMenuResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: Optional[str] = None
    price: int
    is_available: bool
    category: Optional[str] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None


# --------------------------------------------------------------------------- #
# Pesanan
# --------------------------------------------------------------------------- #
class MerchantOrderItemResponse(BaseModel):
    id: int
    menu_id: int
    menu_name: str
    quantity: int
    price: int


class MerchantOrderResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    total_price: int
    delivery_fee: int
    status: str
    delivery_address: str
    notes: Optional[str] = None
    driver_name: Optional[str] = None
    created_at: datetime
    items: List[MerchantOrderItemResponse] = []
    allowed_next_status: List[str] = []


class MerchantOrderStatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=40)
    note: Optional[str] = Field(default=None, max_length=300)


class MerchantOrderEventResponse(BaseModel):
    id: int
    order_id: int
    from_status: Optional[str] = None
    to_status: str
    actor: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Promo
# --------------------------------------------------------------------------- #
class MerchantPromoUpsert(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    discount_type: str = Field(default='percent', pattern='^(percent|amount)$')
    discount_value: int = Field(ge=0, le=100_000_000)
    min_order: int = Field(default=0, ge=0)
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class MerchantPromoResponse(MerchantPromoUpsert):
    id: int
    restaurant_id: int
    created_at: datetime
    applied_at_checkout: bool = False
    note: str = ('Promo disimpan sebagai data; belum diterapkan otomatis di checkout '
                 'pelanggan (butuh perubahan backend order).')

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Keuangan
# --------------------------------------------------------------------------- #
class MerchantBankAccountUpsert(BaseModel):
    bank_name: str = Field(min_length=2, max_length=60)
    account_no: str = Field(min_length=6, max_length=40)
    account_name: str = Field(min_length=2, max_length=80)
    is_primary: bool = False


class MerchantBankAccountResponse(MerchantBankAccountUpsert):
    id: int
    restaurant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MerchantLedgerEntryResponse(BaseModel):
    id: int
    restaurant_id: int
    order_id: Optional[int] = None
    kind: str
    amount: int
    ref: str
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MerchantWithdrawalCreate(BaseModel):
    amount: int = Field(gt=0, le=1_000_000_000)
    bank_name: Optional[str] = Field(default=None, max_length=60)
    account_no: Optional[str] = Field(default=None, max_length=40)
    account_name: Optional[str] = Field(default=None, max_length=80)
    bank_account_id: Optional[int] = None
    client_ref: Optional[str] = Field(default=None, max_length=80,
                                      description='Kunci idempotensi dari aplikasi')


class MerchantWithdrawalResponse(BaseModel):
    id: int
    restaurant_id: int
    amount: int
    bank_name: str
    account_no: str
    account_name: str
    status: str
    client_ref: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MerchantBalanceResponse(BaseModel):
    restaurant_id: int
    ledger_total: int
    pending_withdrawal_total: int
    available_balance: int
    settlements_pending: int
    settlements_approved: int
    note: str = ('Saldo hanya bertambah setelah admin memverifikasi settlement per order. '
                 'Tidak ada kredit histori otomatis dan tidak ada payout otomatis.')


# --------------------------------------------------------------------------- #
# Notifikasi (foreground polling)
# --------------------------------------------------------------------------- #
class MerchantNotification(BaseModel):
    id: str
    kind: str                     # new_order | status_change
    order_id: int
    title: str
    body: str
    created_at: datetime


class MerchantNotificationFeed(BaseModel):
    mode: str = 'foreground_polling'
    note: str = ('Daftar ini hasil polling saat aplikasi terbuka; bukan push notification '
                 'background. Tidak ada FCM/worker server.')
    new_order_cursor: int
    event_cursor: int
    items: List[MerchantNotification] = []


# --------------------------------------------------------------------------- #
# Admin: provisioning, settlement, review withdrawal
# --------------------------------------------------------------------------- #
class AdminMerchantCreate(BaseModel):
    restaurant_id: int
    name: str = Field(min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    restaurant_phone_verified: bool = False
    is_active: bool = True


class AdminMerchantResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminPasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=200)


class AdminSettlementCreate(BaseModel):
    order_id: int
    platform_fee: int = Field(default=0, ge=0)
    note: Optional[str] = Field(default=None, max_length=300)


class AdminSettlementDecision(BaseModel):
    approve: bool = True
    note: Optional[str] = Field(default=None, max_length=300)


class AdminSettlementResponse(BaseModel):
    id: int
    order_id: int
    restaurant_id: int
    gross_amount: int
    delivery_fee: int
    platform_fee: int
    net_amount: int
    status: str
    note: Optional[str] = None
    created_at: datetime
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    ledger_entry_id: Optional[int] = None
    credited: bool = False

    model_config = ConfigDict(from_attributes=True)


class AdminWithdrawalReview(BaseModel):
    action: str = Field(pattern='^(approve|reject|paid)$')
    note: Optional[str] = Field(default=None, max_length=300)


class AdminWithdrawalResponse(MerchantWithdrawalResponse):
    pass
