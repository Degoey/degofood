from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import re

from ..database import get_db
from .. import models, schemas

router = APIRouter()


def _normalize_phone(phone: str) -> str:
    if not phone:
        return phone
    digits = re.sub(r'[^0-9]', '', phone)
    if digits.startswith('62'):
        digits = digits[2:]
    elif digits.startswith('0'):
        digits = digits[1:]
    return '+62' + digits


@router.post('/', response_model=schemas.CustomerResponse)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    data = customer.model_dump()
    data['phone'] = _normalize_phone(data.get('phone', ''))
    db_customer = models.Customer(**data)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get('/', response_model=List[schemas.CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    customers = db.query(models.Customer).all()
    return customers


@router.get('/phone/{phone}', response_model=schemas.CustomerResponse)
def get_customer_by_phone(phone: str, db: Session = Depends(get_db)):
    normalized = _normalize_phone(phone)
    # Try normalized form first, then fallback to raw value
    customer = db.query(models.Customer).filter(models.Customer.phone == normalized).first()
    if not customer:
        customer = db.query(models.Customer).filter(models.Customer.phone == phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    return customer


@router.put('/{customer_id}', response_model=schemas.CustomerResponse)
def update_customer(customer_id: int, customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    db_customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    db_customer.name = customer.name
    db_customer.phone = customer.phone
    db_customer.address = customer.address
    db.commit()
    db.refresh(db_customer)
    return db_customer
