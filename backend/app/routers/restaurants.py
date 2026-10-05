from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter()


@router.get('/', response_model=List[schemas.RestaurantResponse])
def get_open_restaurants(db: Session = Depends(get_db)):
    restaurants = db.query(models.Restaurant).filter(models.Restaurant.is_open == True).all()
    return restaurants


@router.get('/{restaurant_id}', response_model=schemas.RestaurantResponse)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail='Restaurant not found')
    return restaurant


@router.get('/{restaurant_id}/menu', response_model=List[schemas.MenuResponse])
@router.get('/{restaurant_id}/menus', response_model=List[schemas.MenuResponse])
def get_menu(restaurant_id: int, db: Session = Depends(get_db)):
    menus = db.query(models.Menu).filter(
        models.Menu.restaurant_id == restaurant_id,
        models.Menu.is_available == True
    ).all()
    return menus


@router.post('/', response_model=schemas.RestaurantResponse)
def create_restaurant(restaurant: schemas.RestaurantCreate, db: Session = Depends(get_db)):
    db_restaurant = models.Restaurant(**restaurant.model_dump())
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant


@router.post('/menu', response_model=schemas.MenuResponse)
def create_menu(menu: schemas.MenuCreate, db: Session = Depends(get_db)):
    db_menu = models.Menu(**menu.model_dump())
    db.add(db_menu)
    db.commit()
    db.refresh(db_menu)
    return db_menu
