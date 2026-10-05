from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


class MenuCreate(BaseModel):
    restaurant_id: int
    name: str
    description: str
    price: int
    is_available: bool = True


class MenuResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: str
    price: int
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class RestaurantCreate(BaseModel):
    name: str
    address: str
    phone: str
    is_open: bool = True


class RestaurantResponse(RestaurantCreate):
    id: int
    menus: List[MenuResponse] = []

    model_config = ConfigDict(from_attributes=True)


class RestaurantUpdate(BaseModel):
    """Payload untuk mengubah data restoran dari panel admin."""

    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    is_open: Optional[bool] = None


class StatusUpdate(BaseModel):
    """Payload untuk mengubah status pesanan."""

    status: str


class CustomerCreate(BaseModel):
    name: str
    phone: str
    address: str


class CustomerResponse(CustomerCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OrderItemCreate(BaseModel):
    menu_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    menu_id: int
    menu_name: str
    quantity: int
    price: int

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    customer_id: int
    restaurant_id: int
    delivery_address: str
    notes: Optional[str] = None
    items: List[OrderItemCreate]


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    restaurant_id: int
    total_price: int
    delivery_fee: int
    status: str
    delivery_address: str
    notes: Optional[str] = None
    driver_name: Optional[str] = None
    created_at: datetime
    items: List[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AdminSummary(BaseModel):
    """Ringkasan statistik untuk dashboard admin."""

    total_orders: int
    total_restaurants: int
    total_customers: int
    pending_orders: int


class AdminOrderResponse(OrderResponse):
    """Data pesanan ditambah nama pelanggan dan restoran untuk panel admin."""

    customer_name: Optional[str] = None
    restaurant_name: Optional[str] = None
