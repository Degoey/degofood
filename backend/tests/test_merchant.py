"""Uji nyata portal merchant DEGOFOOD (DB sementara, TIDAK menyentuh produksi).

Jalankan:  cd backend && python -m pytest tests/test_merchant.py -q
atau:      cd backend && python tests/test_merchant.py

DATABASE_URL dipaksa ke file sementara sebelum `app` diimpor, jadi DB produksi
(/data/food_delivery.db di container) tidak pernah dibuka.
"""

import os
import sys
import tempfile
import uuid

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='degofood-test-'), 'test.db')
os.environ['DATABASE_URL'] = f'sqlite:///{_TMP_DB}'
os.environ['ADMIN_API_KEY'] = 'test-admin-key'
os.environ['MERCHANT_LOGIN_MAX_FAILS'] = '5'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402

client = TestClient(app)
ADMIN = {'X-Admin-Key': 'test-admin-key'}

PASSED, FAILED = [], []


def check(name, condition, detail=''):
    if condition:
        PASSED.append(name)
        print(f'  PASS  {name}')
    else:
        FAILED.append(f'{name} :: {detail}')
        print(f'  FAIL  {name} :: {detail}')


def seed():
    db = SessionLocal()
    try:
        r1 = models.Restaurant(name='Warung A', address='Jl. A', phone='081200000001', is_open=True)
        r2 = models.Restaurant(name='Warung B', address='Jl. B', phone='081200000002', is_open=True)
        db.add_all([r1, r2])
        db.flush()
        m1 = models.Menu(restaurant_id=r1.id, name='Nasi Goreng', description='pedas', price=20000)
        m2 = models.Menu(restaurant_id=r2.id, name='Mie Ayam', description='biasa', price=15000)
        c1 = models.Customer(name='Budi', phone='+6281200000009', address='Jl. C')
        db.add_all([m1, m2, c1])
        db.flush()
        order = models.Order(customer_id=c1.id, restaurant_id=r1.id, total_price=45000,
                             delivery_fee=5000, status='Menunggu Konfirmasi',
                             delivery_address='Jl. C No. 1')
        db.add(order)
        db.flush()
        db.add(models.OrderItem(order_id=order.id, menu_id=m1.id, menu_name='Nasi Goreng',
                                quantity=2, price=20000))
        db.commit()
        return {'r1': r1.id, 'r2': r2.id, 'm1': m1.id, 'm2': m2.id, 'order': order.id}
    finally:
        db.close()


def main():
    ids = seed()
    print('\n== 1. Provisioning akun oleh admin ==')
    r = client.post('/api/admin/merchants', headers=ADMIN, json={
        'restaurant_id': ids['r1'], 'name': 'Pemilik A', 'phone': '0812-1111-2222',
        'password': 'rahasia123'})
    check('admin buat akun merchant A (HP)', r.status_code == 201, f'{r.status_code} {r.text[:200]}')
    acc_a = r.json() if r.status_code == 201 else {}
    check('nomor HP dinormalisasi ke +62', acc_a.get('phone') == '+6281211112222',
          str(acc_a.get('phone')))

    r = client.post('/api/admin/merchants', headers=ADMIN, json={
        'restaurant_id': ids['r2'], 'name': 'Pemilik B', 'email': 'B@Example.com',
        'password': 'rahasia456'})
    check('admin buat akun merchant B (email)', r.status_code == 201, f'{r.status_code} {r.text[:200]}')
    acc_b = r.json() if r.status_code == 201 else {}
    check('email dinormalisasi lowercase', acc_b.get('email') == 'b@example.com', str(acc_b.get('email')))

    r = client.post('/api/admin/merchants', headers=ADMIN, json={
        'restaurant_id': ids['r1'], 'name': 'Duplikat', 'phone': '0812999',
        'password': 'rahasia123'})
    check('tolak akun kedua untuk restoran sama', r.status_code == 409, f'{r.status_code}')

    r = client.post('/api/admin/merchants', headers=ADMIN, json={
        'restaurant_id': ids['r1'], 'name': 'Pemilik Palsu', 'phone': '081200000001',
        'password': 'rahasia123'})
    check('tolak klaim nomor HP restoran tanpa verifikasi', r.status_code == 409, f'{r.status_code} {r.text[:200]}')

    r = client.get('/api/admin/merchants')
    check('endpoint admin tanpa X-Admin-Key ditolak', r.status_code == 401, f'{r.status_code}')
    r = client.get('/api/admin/merchants', headers={'X-Admin-Key': 'salah'})
    check('endpoint admin dengan key salah ditolak', r.status_code == 401, f'{r.status_code}')

    print('\n== 2. Login (HP atau email + password) ==')
    r = client.post('/api/merchant/auth/login', json={'identifier': '0812-1111-2222', 'password': 'rahasia123'})
    check('login pakai nomor HP', r.status_code == 200, f'{r.status_code} {r.text[:200]}')
    tok_a = r.json().get('token') if r.status_code == 200 else None
    A = {'Authorization': f'Bearer {tok_a}'}

    r = client.post('/api/merchant/auth/login', json={'identifier': 'B@Example.com', 'password': 'rahasia456'})
    check('login pakai email', r.status_code == 200, f'{r.status_code} {r.text[:200]}')
    tok_b = r.json().get('token') if r.status_code == 200 else None
    B = {'Authorization': f'Bearer {tok_b}'}

    r = client.post('/api/merchant/auth/login', json={'identifier': '0812-1111-2222', 'password': 'salah-sekali'})
    check('password salah ditolak 401', r.status_code == 401, f'{r.status_code}')

    r = client.get('/api/merchant/me')
    check('endpoint merchant tanpa token ditolak 401', r.status_code == 401, f'{r.status_code}')
    r = client.get('/api/merchant/me', headers={'Authorization': 'Bearer token-palsu'})
    check('token palsu ditolak 401', r.status_code == 401, f'{r.status_code}')
    r = client.get('/api/merchant/me', headers=A)
    check('GET /me dengan token valid', r.status_code == 200 and r.json()['restaurant_id'] == ids['r1'],
          f'{r.status_code} {r.text[:200]}')

    print('\n== 3. Isolasi antar merchant ==')
    r = client.get(f'/api/merchant/orders/{ids["order"]}', headers=B)
    check('merchant B tidak bisa lihat order merchant A', r.status_code == 404, f'{r.status_code}')
    r = client.get(f'/api/merchant/menus/{ids["m1"]}', headers=B)
    check('merchant B tidak bisa sentuh menu A (via PUT)', client.put(
        f'/api/merchant/menus/{ids["m1"]}', headers=B,
        json={'name': 'Bajakan', 'price': 1}).status_code == 404, 'PUT lintas merchant lolos')
    r = client.get('/api/merchant/menus', headers=A)
    check('merchant A hanya melihat menu miliknya', r.status_code == 200 and
          [m['name'] for m in r.json()] == ['Nasi Goreng'], f'{r.status_code} {r.text[:200]}')

    print('\n== 4. CRUD menu + metadata ==')
    r = client.post('/api/merchant/menus', headers=A, json={
        'name': 'Es Teh', 'price': 5000, 'category': 'Minuman', 'stock': 10, 'is_available': True})
    check('tambah menu baru', r.status_code == 200 and r.json()['category'] == 'Minuman',
          f'{r.status_code} {r.text[:200]}')
    new_menu = r.json().get('id') if r.status_code == 200 else None
    r = client.put(f'/api/merchant/menus/{new_menu}', headers=A, json={
        'name': 'Es Teh Manis', 'price': 6000, 'category': 'Minuman', 'stock': 4, 'is_available': False})
    check('ubah menu (harga/stok/nonaktif)', r.status_code == 200 and r.json()['stock'] == 4
          and r.json()['is_available'] is False, f'{r.status_code} {r.text[:200]}')
    r = client.get('/api/merchant/menu-categories', headers=A)
    check('daftar kategori', r.status_code == 200 and 'Minuman' in r.json()['categories'], f'{r.text[:150]}')
    r = client.delete(f'/api/merchant/menus/{new_menu}', headers=A)
    check('hapus menu', r.status_code == 200, f'{r.status_code}')

    print('\n== 5. Alur status pesanan ==')
    r = client.post(f'/api/merchant/orders/{ids["order"]}/status', headers=A, json={'status': 'Selesai'})
    check('lompat status tidak diizinkan', r.status_code == 409, f'{r.status_code}')
    for target in ['Dikonfirmasi', 'Sedang Dimasak', 'Sedang Diantar', 'Selesai']:
        r = client.post(f'/api/merchant/orders/{ids["order"]}/status', headers=A, json={'status': target})
        check(f'status -> {target}', r.status_code == 200, f'{r.status_code} {r.text[:200]}')
    r = client.post(f'/api/merchant/orders/{ids["order"]}/status', headers=A, json={'status': 'Dibatalkan'})
    check('status final tidak bisa diubah lagi', r.status_code == 409, f'{r.status_code}')
    r = client.get(f'/api/merchant/orders/{ids["order"]}/events', headers=A)
    check('riwayat perubahan status tercatat 4 event', r.status_code == 200 and len(r.json()) == 4,
          f'{r.status_code} {r.text[:200]}')

    print('\n== 6. Profil toko, promo, laporan ==')
    r = client.put('/api/merchant/profile', headers=A, json={
        'description': 'Warung legendaris', 'open_time': '08:00', 'close_time': '21:00',
        'min_order': 10000, 'is_open': True})
    check('ubah profil toko', r.status_code == 200 and r.json()['open_time'] == '08:00',
          f'{r.status_code} {r.text[:200]}')
    r = client.post('/api/merchant/promos', headers=A, json={
        'code': 'gratisongkir', 'title': 'Diskon 10%', 'discount_type': 'percent', 'discount_value': 10})
    check('buat promo (kode jadi HURUF BESAR)', r.status_code == 200 and r.json()['code'] == 'GRATISONGKIR',
          f'{r.status_code} {r.text[:200]}')
    check('promo jujur ditandai belum diterapkan di checkout',
          r.status_code == 200 and r.json().get('applied_at_checkout') is False, str(r.text[:200]))
    r = client.get('/api/merchant/finance/report.csv', headers=A)
    check('ekspor laporan CSV', r.status_code == 200 and 'order_id' in r.text,
          f'{r.status_code} {r.text[:120]}')

    print('\n== 7. Saldo & pencairan (tidak ada uang otomatis) ==')
    r = client.get('/api/merchant/finance/summary', headers=A)
    check('saldo awal 0 (tidak ada kredit histori)', r.status_code == 200 and
          r.json()['available_balance'] == 0, f'{r.text[:200]}')

    r = client.post('/api/merchant/withdrawals', headers=A, json={'amount': 10000, 'bank_name': 'BCA',
                                                                  'account_no': '1234567890',
                                                                  'account_name': 'Pemilik A',
                                                                  'client_ref': 'ref-' + uuid.uuid4().hex[:8]})
    check('pencairan tanpa saldo ditolak', r.status_code == 400, f'{r.status_code} {r.text[:200]}')

    r = client.post('/api/admin/settlements', headers=ADMIN, json={'order_id': ids['order'],
                                                                   'platform_fee': 2000})
    check('admin catat settlement (pending)', r.status_code == 201 and r.json()['status'] == 'pending',
          f'{r.status_code} {r.text[:200]}')
    st = r.json()
    check('net = (total - ongkir) - platform_fee', st.get('net_amount') == 38000, str(st))
    r = client.get('/api/merchant/finance/summary', headers=A)
    check('settlement pending belum menambah saldo', r.json()['available_balance'] == 0, f'{r.text[:200]}')

    r = client.post(f'/api/admin/settlements/{st["id"]}/decision', headers=ADMIN, json={'approve': True})
    check('admin setujui settlement', r.status_code == 200 and r.json()['status'] == 'approved',
          f'{r.status_code} {r.text[:200]}')
    r = client.post(f'/api/admin/settlements/{st["id"]}/decision', headers=ADMIN, json={'approve': True})
    check('approve kedua ditolak (tidak dobel kredit)', r.status_code == 409, f'{r.status_code}')

    r = client.get('/api/merchant/finance/summary', headers=A)
    check('saldo tersedia = 38000 setelah approve', r.json()['available_balance'] == 38000, f'{r.text[:200]}')
    r = client.get('/api/merchant/finance/ledger', headers=A)
    check('ledger berisi tepat 1 entri settlement', len(r.json()) == 1 and r.json()[0]['amount'] == 38000,
          f'{r.text[:200]}')

    ref = 'wd-' + uuid.uuid4().hex[:8]
    body = {'amount': 38000, 'bank_name': 'BCA', 'account_no': '1234567890',
            'account_name': 'Pemilik A', 'client_ref': ref}
    r1 = client.post('/api/merchant/withdrawals', headers=A, json=body)
    check('pengajuan pencairan penuh diterima', r1.status_code == 200, f'{r1.status_code} {r1.text[:200]}')
    r2 = client.post('/api/merchant/withdrawals', headers=A, json=body)
    check('kirim ulang client_ref sama = baris sama (idempoten)',
          r2.status_code == 200 and r2.json()['id'] == r1.json()['id'], f'{r2.status_code} {r2.text[:200]}')
    r3 = client.post('/api/merchant/withdrawals', headers=A, json={**body, 'amount': 1000,
                                                                   'client_ref': 'wd2-' + uuid.uuid4().hex[:8]})
    check('pencairan melebihi saldo ditolak (anti double-spend)', r3.status_code == 400,
          f'{r3.status_code} {r3.text[:200]}')
    r = client.get('/api/merchant/finance/summary', headers=A)
    check('saldo tersedia 0 karena ditahan pengajuan', r.json()['available_balance'] == 0, f'{r.text[:200]}')

    wid = r1.json()['id']
    r = client.post(f'/api/admin/withdrawals/{wid}/review', headers=ADMIN, json={'action': 'paid'})
    check('tandai paid tanpa approve ditolak', r.status_code == 409, f'{r.status_code}')
    r = client.post(f'/api/admin/withdrawals/{wid}/review', headers=ADMIN, json={'action': 'approve'})
    check('admin approve pencairan', r.status_code == 200 and r.json()['status'] == 'approved',
          f'{r.status_code} {r.text[:200]}')
    r = client.post(f'/api/admin/withdrawals/{wid}/review', headers=ADMIN, json={'action': 'paid'})
    check('admin tandai sudah ditransfer (paid)', r.status_code == 200 and r.json()['status'] == 'paid',
          f'{r.status_code} {r.text[:200]}')
    r = client.get('/api/merchant/finance/summary', headers=A)
    check('setelah paid: ledger 38000 - 38000 = saldo 0', r.json()['ledger_total'] == 0 and
          r.json()['available_balance'] == 0, f'{r.text[:200]}')

    print('\n== 8. Notifikasi & kompatibilitas pelanggan ==')
    r = client.get('/api/merchant/notifications?since_order_id=0&since_event_id=0', headers=A)
    check('feed notifikasi polling', r.status_code == 200 and r.json()['mode'] == 'foreground_polling',
          f'{r.status_code} {r.text[:200]}')
    r = client.get('/api/restaurants/')
    check('API pelanggan masih jalan (GET /api/restaurants/)', r.status_code == 200, f'{r.status_code}')
    r = client.get(f'/api/restaurants/{ids["r1"]}/menu')
    check('menu pelanggan masih terbaca', r.status_code == 200, f'{r.status_code} {r.text[:150]}')
    r = client.get('/api/health')
    check('health check', r.status_code == 200, f'{r.status_code}')

    print(f'\n===== HASIL: {len(PASSED)} lulus, {len(FAILED)} gagal =====')
    for f in FAILED:
        print(f'  GAGAL: {f}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
