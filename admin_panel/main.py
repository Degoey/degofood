import os
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / 'templates'

BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '')
SESSION_SECRET = os.getenv('SESSION_SECRET', 'ganti-rahasia')

app = FastAPI(title='DEGOFOOD Admin Panel')
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STATUS_OPTIONS = [
    'Menunggu Konfirmasi',
    'Dikonfirmasi',
    'Sedang Dimasak',
    'Sedang Diantar',
    'Selesai',
    'Dibatalkan',
]


def _api_headers():
    headers = {'Content-Type': 'application/json'}
    if ADMIN_API_KEY:
        headers['X-Admin-Key'] = ADMIN_API_KEY
    return headers


def _api_get(path: str):
    return httpx.get(BACKEND_URL + path, headers=_api_headers(), timeout=10)


def _api_post(path: str, json=None):
    return httpx.post(BACKEND_URL + path, headers=_api_headers(), json=json, timeout=10)


def _api_put(path: str, json=None):
    return httpx.put(BACKEND_URL + path, headers=_api_headers(), json=json, timeout=10)


def _api_delete(path: str):
    return httpx.delete(BACKEND_URL + path, headers=_api_headers(), timeout=10)


def _check_login(request: Request):
    if not request.session.get('admin_user'):
        return RedirectResponse(url='/login', status_code=303)


def format_rupiah(value):
    try:
        return 'Rp ' + '{:,.0f}'.format(value).replace(',', '.')
    except (TypeError, ValueError):
        return 'Rp 0'


def format_datetime(value):
    if not value:
        return '-'
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return value
    return value.strftime('%d-%m-%Y %H:%M')


templates.env.filters['rupiah'] = format_rupiah
templates.env.filters['tanggal'] = format_datetime

@app.get('/login')
def login_page(request: Request, error: str = ''):
    return templates.TemplateResponse(
        request,
        'login.html',
        {'active': 'login', 'error': error},
    )


@app.post('/login')
def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session['admin_user'] = username
        return RedirectResponse(url='/', status_code=303)
    return RedirectResponse(url='/login?error=1', status_code=303)


@app.get('/logout')
def do_logout(request: Request):
    request.session.pop('admin_user', None)
    return RedirectResponse(url='/login', status_code=303)


@app.get('/')
def dashboard(request: Request):
    redirect = _check_login(request)
    if redirect:
        return redirect

    summary = {}
    try:
        r = _api_get('/api/admin/summary')
        if r.status_code == 200:
            summary = r.json()
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        'dashboard.html',
        {
            'active': 'dashboard',
            'total_orders': summary.get('total_orders', 0),
            'total_restaurants': summary.get('total_restaurants', 0),
            'total_customers': summary.get('total_customers', 0),
            'pending_orders': summary.get('pending_orders', 0),
        },
    )


@app.get('/orders')
def orders_page(request: Request):
    redirect = _check_login(request)
    if redirect:
        return redirect

    orders = []
    try:
        r = _api_get('/api/admin/orders')
        if r.status_code == 200:
            orders = r.json()
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        'orders.html',
        {'active': 'orders', 'orders': orders, 'status_options': STATUS_OPTIONS},
    )


@app.post('/orders/{order_id}/status')
def update_order_status(request: Request, order_id: int, status: str = Form(...)):
    try:
        _api_put(f'/api/admin/orders/{order_id}/status', json={'status': status})
    except Exception:
        pass
    return RedirectResponse(url='/orders', status_code=303)


@app.get('/restaurants')
def restaurants_page(request: Request):
    redirect = _check_login(request)
    if redirect:
        return redirect

    restaurants = []
    try:
        r = _api_get('/api/admin/restaurants')
        if r.status_code == 200:
            restaurants = r.json()
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        'restaurants.html',
        {'active': 'restaurants', 'restaurants': restaurants},
    )


@app.post('/restaurants/add')
def add_restaurant(request: Request, name: str = Form(...), address: str = Form(...), phone: str = Form(...)):
    try:
        _api_post('/api/admin/restaurants', json={'name': name, 'address': address, 'phone': phone, 'is_open': True})
    except Exception:
        pass
    return RedirectResponse(url='/restaurants?added=restaurant', status_code=303)


@app.post('/restaurants/{restaurant_id}/menu/add')
def add_menu(request: Request, restaurant_id: int, name: str = Form(...), description: str = Form(''), price: int = Form(...)):
    try:
        _api_post(
            f'/api/admin/restaurants/{restaurant_id}/menus',
            json={'restaurant_id': restaurant_id, 'name': name, 'description': description, 'price': price, 'is_available': True},
        )
    except Exception:
        pass
    return RedirectResponse(url='/restaurants?added=menu', status_code=303)


@app.post('/restaurants/{restaurant_id}/toggle')
def toggle_restaurant(request: Request, restaurant_id: int):
    try:
        _api_put(f'/api/admin/restaurants/{restaurant_id}/toggle')
    except Exception:
        pass
    return RedirectResponse(url='/restaurants', status_code=303)


@app.post('/menus/{menu_id}/toggle')
def toggle_menu(request: Request, menu_id: int):
    try:
        _api_put(f'/api/admin/menus/{menu_id}/toggle')
    except Exception:
        pass
    return RedirectResponse(url='/restaurants', status_code=303)


@app.post('/menus/{menu_id}/delete')
def delete_menu(request: Request, menu_id: int):
    try:
        _api_delete(f'/api/admin/menus/{menu_id}')
    except Exception:
        pass
    return RedirectResponse(url='/restaurants', status_code=303)
