import os
import secrets
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


def _api_patch(path: str, json=None):
    return httpx.patch(BACKEND_URL + path, headers=_api_headers(), json=json, timeout=10)


def _check_login(request: Request):
    if not request.session.get('admin_user'):
        return RedirectResponse(url='/login', status_code=303)


def _csrf(request: Request):
    token = request.session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        request.session['csrf_token'] = token
    return token


def _check_csrf(request: Request, token: str):
    if not token or not secrets.compare_digest(token, request.session.get('csrf_token', '')):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail='CSRF token tidak valid')


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


# --------------------------------------------------------------------------- #
# Merchant: pendaftaran mandiri, akun, persetujuan
# --------------------------------------------------------------------------- #
@app.get('/merchants')
def merchants_page(request: Request, status: str = 'pending', msg: str = '', err: str = ''):
    redirect = _check_login(request)
    if redirect:
        return redirect

    registrations, accounts, restaurants = [], [], []
    try:
        params = f'?status={status}' if status else ''
        r = _api_get('/api/admin/merchant-registrations' + params)
        if r.status_code == 200:
            registrations = r.json()
    except Exception:
        pass
    try:
        r = _api_get('/api/admin/merchants')
        if r.status_code == 200:
            accounts = r.json()
    except Exception:
        pass
    try:
        r = _api_get('/api/admin/restaurants')
        if r.status_code == 200:
            restaurants = r.json()
    except Exception:
        pass

    taken = {a.get('restaurant_id') for a in accounts}
    return templates.TemplateResponse(
        request,
        'merchants.html',
        {'active': 'merchants', 'registrations': registrations, 'accounts': accounts,
         'restaurants': restaurants, 'taken': taken, 'status_filter': status,
         'msg': msg, 'err': err, 'csrf_token': _csrf(request)},
    )


@app.post('/merchants/registrations/{registration_id}/approve')
def approve_registration(request: Request, registration_id: int,
                         csrf_token: str = Form(''),
                         link_mode: str = Form('new'),
                         restaurant_id: str = Form(''),
                         store_name: str = Form(''),
                         store_address: str = Form(''),
                         store_phone: str = Form('')):
    redirect = _check_login(request)
    if redirect:
        return redirect
    _check_csrf(request, csrf_token)
    payload = {}
    if link_mode == 'existing' and restaurant_id.strip():
        payload['restaurant_id'] = int(restaurant_id)
    else:
        payload['new_restaurant'] = {
            'name': store_name.strip() or 'Toko Baru',
            'address': store_address.strip() or '-',
            'phone': store_phone.strip() or '-',
        }
    try:
        r = _api_post(f'/api/admin/merchant-registrations/{registration_id}/approve', json=payload)
        if r.status_code != 200:
            detail = ''
            try:
                detail = str(r.json().get('detail'))
            except Exception:
                detail = r.text[:200]
            return RedirectResponse(url=f'/merchants?err={detail}', status_code=303)
    except Exception as ex:
        return RedirectResponse(url=f'/merchants?err={ex}', status_code=303)
    return RedirectResponse(url='/merchants?msg=Pendaftaran+disetujui+dan+akun+dibuat', status_code=303)


@app.post('/merchants/registrations/{registration_id}/reject')
def reject_registration(request: Request, registration_id: int, csrf_token: str = Form(''), note: str = Form('')):
    redirect = _check_login(request)
    if redirect:
        return redirect
    _check_csrf(request, csrf_token)
    try:
        r = _api_post(f'/api/admin/merchant-registrations/{registration_id}/reject',
                      json={'note': note.strip() or None})
        if r.status_code != 200:
            return RedirectResponse(url=f'/merchants?err={r.text[:200]}', status_code=303)
    except Exception as ex:
        return RedirectResponse(url=f'/merchants?err={ex}', status_code=303)
    return RedirectResponse(url='/merchants?msg=Pendaftaran+ditolak', status_code=303)


@app.post('/merchants/{account_id}/active')
def set_merchant_active(request: Request, account_id: int, csrf_token: str = Form(''), is_active: str = Form('1')):
    redirect = _check_login(request)
    if redirect:
        return redirect
    _check_csrf(request, csrf_token)
    try:
        _api_patch(f'/api/admin/merchants/{account_id}/active?is_active={is_active == "1"}')
    except Exception:
        pass
    return RedirectResponse(url='/merchants?msg=Status+akun+diubah', status_code=303)


@app.post('/merchants/{account_id}/password')
def reset_merchant_password(request: Request, account_id: int, csrf_token: str = Form(''), password: str = Form(...)):
    redirect = _check_login(request)
    if redirect:
        return redirect
    _check_csrf(request, csrf_token)
    try:
        r = _api_post(f'/api/admin/merchants/{account_id}/password', json={'password': password})
        if r.status_code != 200:
            return RedirectResponse(url=f'/merchants?err={r.text[:200]}', status_code=303)
    except Exception as ex:
        return RedirectResponse(url=f'/merchants?err={ex}', status_code=303)
    return RedirectResponse(url='/merchants?msg=Password+direset+dan+token+lama+dicabut', status_code=303)
