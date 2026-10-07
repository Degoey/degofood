"""DEGOFOOD Mobile App.

Aplikasi mobile pemesanan makanan berbasis Flet (Python + Flutter)
yang terhubung ke backend FastAPI DEGOFOOD.
"""

import flet as ft
import httpx
import json
from datetime import datetime

# Alamat backend DEGOFOOD.
# - Desktop dev: http://127.0.0.1:8000
# - APK di jaringan lokal: http://<IP_LAN>:8000
# - Produksi: domain server backend yang sudah dideploy
#   (script build_apk.ps1 -ApiUrl "..." akan menimpa nilai ini saat build)
API_BASE_URL = 'https://api.45.66.153.146.sslip.io'

PRIMARY = ft.Colors.ORANGE_600
ACCENT = ft.Colors.ORANGE_700
BG_COLOR = '#F5F5F5'
DELIVERY_FEE = 5000
CUSTOMER_KEY = 'DEGOFOOD_customer'
SERVER_URL_KEY = 'DEGOFOOD_server_url'


def fmt_price(value):
    """Format angka menjadi rupiah, mis. 25000 -> 'Rp 25.000'."""
    try:
        return 'Rp ' + '{:,.0f}'.format(value).replace(',', '.')
    except Exception:
        return 'Rp 0'


def fmt_date(value):
    """Format tanggal ISO menjadi teks yang mudah dibaca."""
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).strftime('%d %b %Y, %H:%M')
    except Exception:
        return str(value)


def norm_phone(raw):
    """Normalisasi nomor telepon menjadi format +62xxxxxxxxxx."""
    digits = ''.join(ch for ch in str(raw or '') if ch.isdigit())
    if digits.startswith('62'):
        digits = digits[2:]
    elif digits.startswith('0'):
        digits = digits[1:]
    return '+62' + digits if digits else ''


def status_badge(status):
    """Badge kecil berisi status pesanan."""
    color = ft.Colors.ORANGE_600
    if status in ('Dikonfirmasi', 'Sedang Dimasak', 'Sedang Diantar'):
        color = ft.Colors.BLUE_600
    elif status == 'Selesai':
        color = ft.Colors.GREEN_600
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border_radius=ft.border_radius.all(8),
        bgcolor=ft.Colors.with_opacity(0.15, color),
        content=ft.Text(status, size=12, color=color, weight=ft.FontWeight.BOLD),
    )


class APIClient:
    """Pembungkus tipis pemanggilan HTTP ke backend DEGOFOOD."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def get(self, path):
        return httpx.get(self.base_url + path, timeout=10)

    def post(self, path, json_data=None):
        return httpx.post(self.base_url + path, json=json_data, timeout=10)

    def put(self, path, json_data=None):
        return httpx.put(self.base_url + path, json=json_data, timeout=10)

class DEGOFOODApp:
    """Kelas utama yang mengelola UI, state, dan integrasi API."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.customer = None
        self.cart = []
        self.restaurant_id = None
        self.restaurant_name = None
        self.restaurants = []

        self.server_url = self._load_server_url()
        self.api = APIClient(self.server_url)

        page.title = 'DEGOFOOD'
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = BG_COLOR
        page.padding = 0
        page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

        self.nav = ft.NavigationBar(
            selected_index=0,
            on_change=self.nav_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME, label='Home'),
                ft.NavigationBarDestination(icon=ft.Icons.SHOPPING_CART, label='Cart'),
                ft.NavigationBarDestination(icon=ft.Icons.RECEIPT, label='Orders'),
                ft.NavigationBarDestination(icon=ft.Icons.PERSON, label='Profile'),
            ],
            bgcolor=ft.Colors.WHITE,
            indicator_color=ft.Colors.ORANGE_100,
            indicator_shape=ft.RoundedRectangleBorder(radius=12),
        )
        self.load_customer()

    # ---- Helpers ----
    def snack(self, msg, color=PRIMARY):
        self.page.open(ft.SnackBar(
            content=ft.Text(str(msg), color=ft.Colors.WHITE),
            bgcolor=color,
            duration=2500,
        ))

    def load_customer(self):
        try:
            self.customer = json.loads(self.page.client_storage.get(CUSTOMER_KEY) or '{}') or None
        except Exception:
            self.customer = None

    def save_customer(self):
        if self.customer:
            self.page.client_storage.set(CUSTOMER_KEY, json.dumps(self.customer))
        else:
            self.page.client_storage.remove(CUSTOMER_KEY)

    def _load_server_url(self):
        try:
            return self.page.client_storage.get(SERVER_URL_KEY) or API_BASE_URL
        except Exception:
            return API_BASE_URL

    def _save_server_url(self, url: str):
        try:
            self.page.client_storage.set(SERVER_URL_KEY, url)
        except Exception:
            pass

    def set_server_url(self, url: str):
        url = url.strip()
        if not url:
            return
        if not url.startswith(('http://', 'https://')):
            return self.snack('URL harus diawali http:// atau https://', ft.Colors.RED_400)
        self.server_url = url.rstrip('/')
        self.api = APIClient(self.server_url)
        self._save_server_url(self.server_url)
        self.snack(f'Server diset ke {self.server_url}', ft.Colors.GREEN_700)

    def server_dialog(self):
        def save(e):
            self.set_server_url(field.value)
            self.page.close(dlg)

        field = ft.TextField(label='URL Server Backend', value=self.server_url, prefix_text='')
        dlg = ft.AlertDialog(
            title=ft.Text('Pengaturan Server'),
            content=ft.Column(
                [ft.Text('Masukkan URL backend, contoh: http://192.168.1.10:8000'), field],
                tight=True,
                spacing=12,
            ),
            actions=[
                ft.TextButton('Batal', on_click=lambda e: self.page.close(dlg)),
                ft.ElevatedButton('Simpan', on_click=save, bgcolor=PRIMARY, color=ft.Colors.WHITE),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    def header(self, title, subtitle=None, back=None, actions=None):
        rows = [ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=back)] if back else []
        rows.append(ft.Text(title, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, expand=True))
        if actions:
            rows.extend(actions)
        controls = [ft.Row(controls=rows, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]
        if subtitle:
            controls.append(ft.Text(subtitle, size=14, color=ft.Colors.WHITE70))
        return ft.Container(
            height=160,
            padding=ft.padding.only(left=16 if back else 24, right=24, top=40, bottom=24),
            border_radius=ft.border_radius.only(bottom_left=24, bottom_right=24),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[ft.Colors.ORANGE_400, ft.Colors.ORANGE_700],
            ),
            content=ft.Column(
                alignment=ft.MainAxisAlignment.END,
                cross_axis_alignment=ft.CrossAxisAlignment.START,
                spacing=4,
                controls=controls,
            ),
        )

    def empty(self, icon, text, btn=None):
        controls = [
            ft.Icon(icon, size=80, color=ft.Colors.GREY_400),
            ft.Text(text, text_align=ft.TextAlign.CENTER, size=16, color=ft.Colors.GREY_600),
        ]
        if btn:
            controls.extend([ft.Container(height=16), btn])
        return ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            controls=controls,
        )

    # ---- Authentication ----
    def auth_dialog(self):
        phone = ft.TextField(label='Nomor Telepon', prefix_text='+62 ', keyboard_type=ft.KeyboardType.PHONE)

        def login(e):
            p = norm_phone(phone.value)
            if len(p) < 10:
                return self.snack('Nomor telepon tidak valid', ft.Colors.RED_400)
            r = self.api.get(f'/api/customers/phone/{p}')
            if r.status_code == 404:
                return self.register_dialog(p)
            r.raise_for_status()
            self.customer = r.json()
            self.save_customer()
            self.page.close(dlg)
            self.snack(f"Selamat datang, {self.customer['name']}!")
            self.home()

        dlg = ft.AlertDialog(
            title=ft.Text('Masuk ke DEGOFOOD'),
            content=ft.Column([ft.Text('Masukkan nomor telepon.'), phone], tight=True, spacing=12),
            actions=[
                ft.TextButton('Daftar', on_click=lambda e: self.register_dialog()),
                ft.ElevatedButton('Masuk', on_click=login, bgcolor=PRIMARY, color=ft.Colors.WHITE),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    def register_dialog(self, phone=''):
        name = ft.TextField(label='Nama Lengkap', autofocus=True)
        phone_f = ft.TextField(label='Nomor Telepon', prefix_text='+62 ',
                                value=phone[3:] if phone.startswith('+62') else phone)
        address = ft.TextField(label='Alamat Pengiriman', multiline=True, min_lines=2, max_lines=4)

        def submit(e):
            self.snack('Tombol Daftar ditekan', ft.Colors.BLUE_400)
            btn.disabled = True
            btn.text = 'Memproses...'
            self.page.update()
            try:
                p = norm_phone(phone_f.value)
                if not (name.value.strip() and p and len(p) >= 10 and address.value.strip()):
                    self.snack('Lengkapi semua data', ft.Colors.RED_400)
                    return
                r = self.api.post('/api/customers/', json_data={
                    'name': name.value.strip(),
                    'phone': p,
                    'address': address.value.strip(),
                })
                r.raise_for_status()
                self.customer = r.json()
                self.save_customer()
                self.page.close(dlg)
                self.snack('Akun berhasil dibuat!', ft.Colors.GREEN_700)
                self.home()
            except Exception as ex:
                self.snack(f'Gagal daftar: {str(ex)}', ft.Colors.RED_400)
            finally:
                btn.disabled = False
                btn.text = 'Daftar'
                self.page.update()

        btn = ft.ElevatedButton('Daftar', on_click=submit, bgcolor=PRIMARY, color=ft.Colors.WHITE)
        dlg = ft.AlertDialog(
            title=ft.Text('Daftar Akun'),
            content=ft.Column([name, phone_f, address], tight=True, spacing=12),
            actions=[btn],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    # ---- Navigation ----
    def nav_change(self, e):
        index = e.control.selected_index
        if index == 0:
            self.home()
        elif index == 1:
            self.cart_page()
        elif index == 2:
            self.orders_page()
        else:
            self.profile_page()

    def start(self):
        if self.customer:
            self.home()
        else:
            self.welcome_page()

    def welcome_page(self):
        self.page.views.clear()
        self.page.views.append(ft.View('/welcome', padding=0, controls=[
            ft.Stack(
                expand=True,
                controls=[
                    ft.Column(
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=24,
                        controls=[
                            ft.Icon(ft.Icons.DELIVERY_DINING, size=120, color=PRIMARY),
                            ft.Text('DEGOFOOD', size=40, weight=ft.FontWeight.BOLD, color=ACCENT),
                            ft.Text('Pesan makanan favoritmu dengan mudah', size=16, color=ft.Colors.GREY_600),
                            ft.ElevatedButton(
                                'Mulai Sekarang',
                                on_click=lambda e: self.auth_dialog(),
                                bgcolor=PRIMARY,
                                color=ft.Colors.WHITE,
                                width=250,
                                height=50,
                            ),
                        ],
                    ),
                    ft.Container(
                        alignment=ft.alignment.top_right,
                        padding=ft.padding.only(top=40, right=24),
                        content=ft.IconButton(
                            icon=ft.Icons.SETTINGS,
                            icon_color=ft.Colors.GREY_700,
                            on_click=lambda e: self.server_dialog(),
                            tooltip='Pengaturan Server',
                        ),
                    ),
                ],
            )
        ]))
        self.page.update()

    # ---- Home ----
    def home(self):
        self.nav.selected_index = 0
        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        loading = ft.ProgressRing(visible=True, width=30, height=30)
        err = ft.Text('', color=ft.Colors.RED_400, size=14, text_align=ft.TextAlign.CENTER)

        def search(e):
            query = e.control.value.lower()
            filtered = [r for r in self.restaurants
                        if query in r.get('name', '').lower() or query in r.get('address', '').lower()]
            self.render_restaurants(col, filtered)

        def load(e=None):
            loading.visible = True
            self.page.update()
            try:
                r = self.api.get('/api/restaurants/')
                r.raise_for_status()
                self.restaurants = r.json()
                self.render_restaurants(col, self.restaurants)
                err.value = ''
            except Exception:
                err.value = 'Gagal memuat restoran. Pastikan backend berjalan.'
            finally:
                loading.visible = False
                self.page.update()

        self.page.views.clear()
        self.page.views.append(ft.View('/', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header(
                    'DEGOFOOD',
                    subtitle='Pesan makanan favoritmu',
                    actions=[
                        ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=ft.Colors.WHITE, on_click=lambda e: self.server_dialog(), tooltip='Pengaturan Server'),
                        ft.IconButton(icon=ft.Icons.REFRESH, icon_color=ft.Colors.WHITE, on_click=load),
                    ],
                ),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    ft.TextField(
                        hint_text='Cari restoran...',
                        prefix_icon=ft.Icons.SEARCH,
                        filled=True,
                        fill_color=ft.Colors.WHITE,
                        border_radius=ft.border_radius.all(12),
                        on_change=search,
                    ),
                    ft.Text('Restoran Terdekat', size=18, weight=ft.FontWeight.BOLD),
                    loading,
                    err,
                    col,
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()
        load()

    def render_restaurants(self, col, items):
        col.controls.clear()
        if not items:
            col.controls.append(self.empty(ft.Icons.RESTAURANT_MENU, 'Tidak ada restoran ditemukan'))
        else:
            for r in items:
                col.controls.append(self.restaurant_card(r))
        self.page.update()

    def restaurant_card(self, restaurant):
        def open_menu(e):
            self.restaurant_id = restaurant['id']
            self.restaurant_name = restaurant['name']
            self.menu_page()

        return ft.Card(
            elevation=3,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.ListTile(
                leading=ft.CircleAvatar(
                    content=ft.Icon(ft.Icons.RESTAURANT, color=PRIMARY),
                    bgcolor=ft.Colors.ORANGE_50,
                ),
                title=ft.Text(restaurant.get('name', 'Restoran'), weight=ft.FontWeight.BOLD, size=16),
                subtitle=ft.Text(restaurant.get('address', ''), color=ft.Colors.GREY_600, size=13),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_400),
                on_click=open_menu,
            ),
        )

    # ---- Menu ----
    def menu_page(self):
        loading = ft.ProgressRing(visible=True, width=30, height=30)
        err = ft.Text('', color=ft.Colors.RED_400, size=14, text_align=ft.TextAlign.CENTER)
        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)

        def load(e=None):
            loading.visible = True
            self.page.update()
            try:
                r = self.api.get(f'/api/restaurants/{self.restaurant_id}/menu')
                r.raise_for_status()
                items = r.json()
                col.controls.clear()
                if not items:
                    col.controls.append(self.empty(ft.Icons.FASTFOOD, 'Menu kosong'))
                else:
                    for it in items:
                        col.controls.append(self.menu_card(it))
                err.value = ''
            except Exception:
                err.value = 'Gagal memuat menu. Pastikan backend berjalan.'
            finally:
                loading.visible = False
                self.page.update()

        self.page.views.clear()
        self.page.views.append(ft.View('/menu', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Menu', subtitle=self.restaurant_name, back=lambda e: self.home()),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    loading,
                    err,
                    col,
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()
        load()

    def menu_card(self, item):
        def add(e):
            existing = next((i for i in self.cart if i['menu_id'] == item['id']), None)
            if existing:
                existing['quantity'] += 1
            else:
                self.cart.append({
                    'menu_id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': 1,
                })
            self.snack(f"{item['name']} ditambahkan", ft.Colors.GREEN_700)
            self.update_badge()

        return ft.Card(
            elevation=3,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(item.get('name', 'Menu'), weight=ft.FontWeight.BOLD, size=16, expand=True),
                                ft.Text(fmt_price(item.get('price', 0)), color=ACCENT, weight=ft.FontWeight.BOLD, size=14),
                            ],
                        ),
                        ft.Text(item.get('description', ''), color=ft.Colors.GREY_600, size=13),
                        ft.ElevatedButton(
                            'Tambah',
                            icon=ft.Icons.ADD_SHOPPING_CART,
                            color=ft.Colors.WHITE,
                            bgcolor=PRIMARY,
                            on_click=add,
                        ),
                    ],
                ),
            ),
        )

    def update_badge(self):
        total = sum(i['quantity'] for i in self.cart)
        self.nav.destinations[1].label = f'Cart ({total})' if total else 'Cart'
        self.page.update()

    # ---- Cart ----
    def cart_page(self):
        if not self.customer:
            self.page.views.clear()
            self.page.views.append(ft.View('/cart', padding=0, controls=[
                ft.Column(expand=True, spacing=0, controls=[
                    self.header('Keranjang'),
                    self.empty(
                        ft.Icons.LOGIN,
                        'Silakan masuk untuk mengakses keranjang',
                        ft.ElevatedButton('Masuk / Daftar', on_click=lambda e: self.auth_dialog(), bgcolor=PRIMARY, color=ft.Colors.WHITE),
                    ),
                ])
            ]))
            self.page.navigation_bar = self.nav
            self.page.update()
            return

        addr = ft.TextField(label='Alamat Pengiriman', value=self.customer.get('address', ''), multiline=True, min_lines=2, max_lines=4)
        notes = ft.TextField(label='Catatan (opsional)', multiline=True, min_lines=2, max_lines=4)
        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        sub = ft.Text(fmt_price(0), weight=ft.FontWeight.BOLD, size=14)
        total = ft.Text(fmt_price(DELIVERY_FEE), weight=ft.FontWeight.BOLD, size=20, color=ACCENT)
        btn = ft.ElevatedButton(
            'PESAN SEKARANG',
            width=400,
            height=50,
            color=ft.Colors.WHITE,
            bgcolor=PRIMARY,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        )

    # ---- Orders ----
    def orders_page(self):
        if not self.customer:
            self.page.views.clear()
            self.page.views.append(ft.View('/orders', padding=0, controls=[
                ft.Column(expand=True, spacing=0, controls=[
                    self.header('Riwayat Pesanan'),
                    self.empty(
                        ft.Icons.RECEIPT_LONG,
                        'Silakan masuk untuk melihat riwayat pesanan',
                        ft.ElevatedButton('Masuk / Daftar', on_click=lambda e: self.auth_dialog(), bgcolor=PRIMARY, color=ft.Colors.WHITE),
                    ),
                ])
            ]))
            self.page.navigation_bar = self.nav
            self.page.update()
            return

        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        loading = ft.ProgressRing(visible=True, width=30, height=30)
        err = ft.Text('', color=ft.Colors.RED_400, size=14, text_align=ft.TextAlign.CENTER)

        def load(e=None):
            loading.visible = True
            self.page.update()
            try:
                r = self.api.get(f'/api/orders/customer/{self.customer["id"]}')
                r.raise_for_status()
                orders = r.json()
                col.controls.clear()
                if not orders:
                    col.controls.append(self.empty(ft.Icons.RECEIPT_LONG, 'Belum ada pesanan'))
                else:
                    for o in orders:
                        col.controls.append(self.order_card(o))
                err.value = ''
            except Exception:
                err.value = 'Gagal memuat pesanan. Pastikan backend berjalan.'
            finally:
                loading.visible = False
                self.page.update()

        self.page.views.clear()
        self.page.views.append(ft.View('/orders', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Riwayat Pesanan', actions=[
                    ft.IconButton(icon=ft.Icons.REFRESH, icon_color=ft.Colors.WHITE, on_click=load),
                ]),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    loading,
                    err,
                    col,
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()
        load()

    def order_card(self, order):
        def on_click(e):
            self.order_detail(order)

        return ft.Card(
            elevation=3,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text('Order #' + str(order['id']), weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(fmt_date(order['created_at']), color=ft.Colors.GREY_600, size=13),
                            ],
                        ),
                        status_badge(order['status']),
                        ft.Text(order.get('delivery_address', ''), color=ft.Colors.GREY_600, size=13),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text('Total', weight=ft.FontWeight.BOLD, size=14),
                                ft.Text(fmt_price(order.get('total_price', 0)), weight=ft.FontWeight.BOLD, size=16, color=ACCENT),
                            ],
                        ),
                    ],
                ),
            ),
        )

    def order_detail(self, order):
        items_text = '\n'.join([f"- {i['menu_name']} x{i['quantity']} @ {fmt_price(i['price'])}" for i in order.get('items', [])])
        content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            controls=[
                ft.Text('Detail Pesanan', size=20, weight=ft.FontWeight.BOLD),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Order ID'), ft.Text('#' + str(order['id']), weight=ft.FontWeight.BOLD)]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Tanggal'), ft.Text(fmt_date(order['created_at']))]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Status'), status_badge(order['status'])]),
                ft.Divider(),
                ft.Text('Item', size=16, weight=ft.FontWeight.BOLD),
                ft.Text(items_text or '-'),
                ft.Divider(),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Subtotal'), ft.Text(fmt_price(order['total_price'] - order['delivery_fee']))]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Ongkir'), ft.Text(fmt_price(order['delivery_fee']))]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Total', weight=ft.FontWeight.BOLD), ft.Text(fmt_price(order['total_price']), weight=ft.FontWeight.BOLD, color=ACCENT, size=18)]),
                ft.Divider(),
                ft.Text('Alamat Pengiriman', size=16, weight=ft.FontWeight.BOLD),
                ft.Text(order.get('delivery_address', '-')),
                ft.Text('Catatan', size=16, weight=ft.FontWeight.BOLD),
                ft.Text(order.get('notes') or '-'),
            ],
        )
        self.page.views.clear()
        self.page.views.append(ft.View('/order-detail', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Detail Pesanan', back=lambda e: self.orders_page()),
                ft.Container(expand=True, padding=16, content=content),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()

    # ---- Profile ----
    def profile_page(self):
        if not self.customer:
            self.page.views.clear()
            self.page.views.append(ft.View('/profile', padding=0, controls=[
                ft.Column(expand=True, spacing=0, controls=[
                    self.header('Profil'),
                    self.empty(
                        ft.Icons.PERSON_OUTLINE,
                        'Silakan masuk terlebih dahulu',
                        ft.ElevatedButton('Masuk / Daftar', on_click=lambda e: self.auth_dialog(), bgcolor=PRIMARY, color=ft.Colors.WHITE),
                    ),
                ])
            ]))
            self.page.navigation_bar = self.nav
            self.page.update()
            return

        name = ft.TextField(label='Nama Lengkap', value=self.customer.get('name', ''))
        phone = ft.TextField(label='Nomor Telepon', value=self.customer.get('phone', ''), read_only=True)
        addr = ft.TextField(label='Alamat', value=self.customer.get('address', ''), multiline=True, min_lines=2, max_lines=4)

        def save(e):
            if not name.value.strip() or not addr.value.strip():
                return self.snack('Nama dan alamat wajib diisi', ft.Colors.RED_400)
            try:
                r = self.api.put(f'/api/customers/{self.customer["id"]}', json_data={
                    'name': name.value.strip(),
                    'phone': self.customer['phone'],
                    'address': addr.value.strip(),
                })
                r.raise_for_status()
                self.customer = r.json()
                self.save_customer()
                self.snack('Profil berhasil diperbarui', ft.Colors.GREEN_700)
            except Exception as ex:
                self.snack('Gagal memperbarui profil: ' + str(ex), ft.Colors.RED_400)

        def logout(e):
            self.customer = None
            self.cart.clear()
            self.save_customer()
            self.snack('Berhasil keluar', ft.Colors.BLUE_600)
            self.home()

        self.page.views.clear()
        self.page.views.append(ft.View('/profile', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Profil'),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    ft.Card(
                        elevation=3,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=16),
                        content=ft.Container(
                            padding=20,
                            content=ft.Column(
                                spacing=12,
                                controls=[
                                    ft.Text('Informasi Akun', size=18, weight=ft.FontWeight.BOLD),
                                    name,
                                    phone,
                                    addr,
                                    ft.ElevatedButton('Simpan Perubahan', on_click=save, bgcolor=PRIMARY, color=ft.Colors.WHITE, width=400),
                                ],
                            ),
                        ),
                    ),
                    ft.ElevatedButton('Keluar', on_click=logout, bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE, width=400),
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()


def main(page: ft.Page):
    app = DEGOFOODApp(page)
    app.start()


if __name__ == '__main__':
    ft.app(target=main)
