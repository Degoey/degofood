import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from . import merchant_models  # noqa: F401  -- daftarkan tabel merchant sebelum create_all
from .routers import restaurants, customers, orders, admin, merchant, admin_merchant

app = FastAPI(title='DEGOFOOD API')


@app.middleware('http')
async def _security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    return response


_cors_origins = os.getenv('CORS_ORIGINS', '*')
allow_origins = [o.strip() for o in _cors_origins.split(',')] if _cors_origins != '*' else ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

Base.metadata.create_all(bind=engine)

app.include_router(restaurants.router, prefix='/api/restaurants', tags=['Restaurants'])
app.include_router(customers.router, prefix='/api/customers', tags=['Customers'])
app.include_router(orders.router, prefix='/api/orders', tags=['Orders'])
app.include_router(admin.router, prefix='/api/admin', tags=['Admin'])
app.include_router(merchant.router, prefix='/api/merchant', tags=['Merchant'])
app.include_router(admin_merchant.router, prefix='/api/admin', tags=['Admin Merchant'])


@app.get('/')
def read_root():
    return {'message': 'DEGOFOOD API is running!'}


@app.get('/api/health')
def health_check():
    return {'status': 'ok'}
