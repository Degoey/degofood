import json
import os
import sys
import httpx

BASE_BACKEND = os.getenv('BASE_BACKEND', 'http://127.0.0.1:8000')
BASE_ADMIN = os.getenv('BASE_ADMIN', 'http://127.0.0.1:8001')

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')


def main():
    client = httpx.Client(follow_redirects=True)

    # 0. Login ke admin panel (halaman admin dilindungi sesi login)
    resp = client.post(
        f'{BASE_ADMIN}/login',
        data={'username': ADMIN_USERNAME, 'password': ADMIN_PASSWORD},
    )
    print('POST /login status:', resp.status_code)
    if 'name="password"' in resp.text or 'Masuk' in resp.text:
        print('Gagal login ke admin panel, periksa ADMIN_USERNAME/ADMIN_PASSWORD')
        sys.exit(1)

    # 1. Tambah restoran via admin panel
    resp = client.post(
        f'{BASE_ADMIN}/restaurants/add',
        data={'name': 'Restoran Bagian 9', 'address': 'Jl. Testing No. 9', 'phone': '089876543210'},
    )
    print('POST /restaurants/add status:', resp.status_code)

    # 2. Ambil daftar restoran untuk dapatkan ID (dari atribut data-id tombol Tambah Menu)
    resp = client.get(f'{BASE_ADMIN}/restaurants')
    print('GET /restaurants status:', resp.status_code)
    import re
    matches = re.findall(r'data-id="(\d+)"', resp.text)
    if not matches:
        print('Gagal menemukan ID restoran di halaman admin')
        sys.exit(1)
    # Ambil ID restoran pertama yang bukan 0 (placeholder modal)
    restaurant_id = next(int(mid) for mid in matches if mid != '0')
    print('Restaurant ID:', restaurant_id)

    # 3. Tambah menu via admin panel
    resp = client.post(
        f'{BASE_ADMIN}/restaurants/{restaurant_id}/menu/add',
        data={'name': 'Nasi Goreng Bag 9', 'description': 'Nasi goreng spesial', 'price': '28000'},
    )
    print('POST menu add status:', resp.status_code)

    # 4. Ambil menu dari backend
    resp = client.get(f'{BASE_BACKEND}/api/restaurants/{restaurant_id}/menu')
    menus = resp.json()
    print('Menus:', menus)
    if not menus:
        print('Menu tidak ditemukan')
        sys.exit(1)
    menu_id = menus[0]['id']

    # 5. Buat customer
    resp = client.post(
        f'{BASE_BACKEND}/api/customers/',
        json={'name': 'Customer Bag 9', 'phone': '081234567899', 'address': 'Jl. Customer No. 9'},
    )
    print('Create customer status:', resp.status_code)
    customer_id = resp.json()['id']

    # 6. Buat order
    resp = client.post(
        f'{BASE_BACKEND}/api/orders/',
        json={
            'customer_id': customer_id,
            'restaurant_id': restaurant_id,
            'delivery_address': 'Jl. Customer No. 9, Kota Testing',
            'notes': 'Test BAGIAN 9',
            'items': [{'menu_id': menu_id, 'quantity': 2}],
        },
    )
    print('Create order status:', resp.status_code)
    order = resp.json()
    print('Order:', json.dumps(order, indent=2))

    # 7. Update status order via backend PUT (simulasi admin update)
    resp = client.put(f"{BASE_BACKEND}/api/orders/{order['id']}/status", params={'status': 'Selesai'})
    print('Update status status:', resp.status_code)
    print('Update status body:', resp.json())


if __name__ == '__main__':
    main()
