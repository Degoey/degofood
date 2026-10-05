from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..services.whatsapp import send_whatsapp_message

router = APIRouter()


def format_rupiah(amount: int) -> str:
    """Format angka menjadi rupiah, mis. 25000 -> 'Rp 25.000'."""
    try:
        return 'Rp ' + '{:,.0f}'.format(amount).replace(',', '.')
    except (TypeError, ValueError):
        return 'Rp 0'


@router.post('/', response_model=schemas.OrderResponse)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')

    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == order.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail='Restaurant not found')

    delivery_fee = 5000
    total_price = delivery_fee
    order_items = []

    for item in order.items:
        menu = db.query(models.Menu).filter(models.Menu.id == item.menu_id).first()
        if not menu:
            raise HTTPException(status_code=404, detail=f'Menu with id {item.menu_id} not found')

        item_total = menu.price * item.quantity
        total_price += item_total

        order_items.append(models.OrderItem(
            menu_id=menu.id,
            menu_name=menu.name,
            quantity=item.quantity,
            price=menu.price
        ))

    db_order = models.Order(
        customer_id=order.customer_id,
        restaurant_id=order.restaurant_id,
        delivery_address=order.delivery_address,
        notes=order.notes,
        delivery_fee=delivery_fee,
        total_price=total_price,
        items=order_items
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Notifikasi ke restoran bahwa ada pesanan baru masuk
    send_whatsapp_message(
        restaurant.phone,
        f'Halo {restaurant.name}, ada pesanan baru! '
        f'Total: {format_rupiah(db_order.total_price)}. Mohon segera diproses.'
    )

    return db_order


@router.get('/', response_model=List[schemas.OrderResponse])
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).all()
    return orders


@router.get('/customer/{customer_id}', response_model=List[schemas.OrderResponse])
def get_orders_by_customer(customer_id: int, db: Session = Depends(get_db)):
    orders = db.query(models.Order).filter(
        models.Order.customer_id == customer_id
    ).order_by(models.Order.created_at.desc()).all()
    return orders


@router.put('/{order_id}/status')
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail='Order not found')

    db_order.status = status
    db.commit()
    db.refresh(db_order)

    # Notifikasi ke customer bahwa status pesanannya berubah
    customer = db.query(models.Customer).filter(
        models.Customer.id == db_order.customer_id
    ).first()
    if customer:
        send_whatsapp_message(
            customer.phone,
            f'Halo {customer.name}, status pesanan #{db_order.id} Anda '
            f'berubah menjadi: {db_order.status}.'
        )

    return {'message': 'Status pesanan berhasil diperbarui', 'order_id': db_order.id, 'status': db_order.status}
