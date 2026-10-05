import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..services.whatsapp import send_whatsapp_message

router = APIRouter(tags=['Admin'])


def _require_admin_key(x_admin_key: Optional[str] = Header(default=None)):
    expected = os.getenv('ADMIN_API_KEY', '')
    if expected and x_admin_key != expected:
        raise HTTPException(status_code=401, detail='Admin API key tidak valid')
    return x_admin_key


@router.get('/summary', response_model=schemas.AdminSummary)
def admin_summary(db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    return {
        'total_orders': db.query(models.Order).count(),
        'total_restaurants': db.query(models.Restaurant).count(),
        'total_customers': db.query(models.Customer).count(),
        'pending_orders': db.query(models.Order).filter(models.Order.status == 'Menunggu Konfirmasi').count(),
    }


@router.get('/restaurants', response_model=List[schemas.RestaurantResponse])
def admin_restaurants(db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    return db.query(models.Restaurant).order_by(models.Restaurant.id).all()


@router.post('/restaurants', response_model=schemas.RestaurantResponse)
def admin_create_restaurant(data: schemas.RestaurantCreate, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    db_restaurant = models.Restaurant(**data.model_dump())
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant


@router.put('/restaurants/{restaurant_id}', response_model=schemas.RestaurantResponse)
def admin_update_restaurant(restaurant_id: int, data: schemas.RestaurantUpdate, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail='Restaurant not found')
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(restaurant, key, value)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.put('/restaurants/{restaurant_id}/toggle', response_model=schemas.RestaurantResponse)
def admin_toggle_restaurant(restaurant_id: int, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail='Restaurant not found')
    restaurant.is_open = not restaurant.is_open
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.delete('/restaurants/{restaurant_id}')
def admin_delete_restaurant(restaurant_id: int, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail='Restaurant not found')
    db.delete(restaurant)
    db.commit()
    return {'message': 'Restoran berhasil dihapus'}


@router.post('/restaurants/{restaurant_id}/menus', response_model=schemas.MenuResponse)
def admin_create_menu(restaurant_id: int, data: schemas.MenuCreate, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    menu = models.Menu(**data.model_dump())
    menu.restaurant_id = restaurant_id
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


@router.put('/menus/{menu_id}/toggle', response_model=schemas.MenuResponse)
def admin_toggle_menu(menu_id: int, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail='Menu not found')
    menu.is_available = not menu.is_available
    db.commit()
    db.refresh(menu)
    return menu


@router.delete('/menus/{menu_id}')
def admin_delete_menu(menu_id: int, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail='Menu not found')
    db.delete(menu)
    db.commit()
    return {'message': 'Menu berhasil dihapus'}


@router.get('/orders', response_model=List[schemas.AdminOrderResponse])
def admin_orders(db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).all()
    customers = {c.id: c.name for c in db.query(models.Customer).all()}
    restaurants = {r.id: r.name for r in db.query(models.Restaurant).all()}
    result = []
    for order in orders:
        data = schemas.OrderResponse.model_validate(order).model_dump()
        data['customer_name'] = customers.get(order.customer_id)
        data['restaurant_name'] = restaurants.get(order.restaurant_id)
        result.append(data)
    return result


@router.put('/orders/{order_id}/status')
def admin_update_order_status(order_id: int, data: schemas.StatusUpdate, db: Session = Depends(get_db), _=Depends(_require_admin_key)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail='Order not found')
    db_order.status = data.status
    db.commit()
    db.refresh(db_order)
    customer = db.query(models.Customer).filter(models.Customer.id == db_order.customer_id).first()
    if customer:
        send_whatsapp_message(
            customer.phone,
            f'Halo {customer.name}, status pesanan #{db_order.id} Anda berubah menjadi: {db_order.status}.'
        )
    return {'message': 'Status pesanan berhasil diperbarui', 'order_id': db_order.id, 'status': db_order.status}
