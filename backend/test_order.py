import httpx

BASE = 'http://127.0.0.1:8000'


def test_customers():
    r = httpx.get(f'{BASE}/api/customers/')
    print('GET /api/customers/', r.status_code, r.json())
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    assert data[0]['name'] == 'Budi Santoso'


def test_create_order():
    payload = {
        "customer_id": 1,
        "restaurant_id": 1,
        "delivery_address": "Jl. Merdeka No. 1",
        "notes": "Test order",
        "items": [
            {"menu_id": 1, "quantity": 1}
        ]
    }
    r = httpx.post(f'{BASE}/api/orders/', json=payload)
    print('POST /api/orders/', r.status_code, r.text)
    assert r.status_code == 200
    data = r.json()
    assert data['total_price'] == 30000  # 25000 + 5000
    assert data['delivery_fee'] == 5000
    assert data['status'] == 'Menunggu Konfirmasi'
    assert len(data['items']) == 1
    assert data['items'][0]['menu_name'] == 'Nasi Padang Komplit'
    return data['id']


def test_get_orders():
    r = httpx.get(f'{BASE}/api/orders/')
    print('GET /api/orders/', r.status_code, r.json())
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0


def test_update_status(order_id):
    r = httpx.put(f'{BASE}/api/orders/{order_id}/status', params={'status': 'Dikonfirmasi'})
    print(f'PUT /api/orders/{order_id}/status', r.status_code, r.json())
    assert r.status_code == 200


if __name__ == '__main__':
    test_customers()
    order_id = test_create_order()
    test_get_orders()
    test_update_status(order_id)
    print('Semua tes berhasil!')
