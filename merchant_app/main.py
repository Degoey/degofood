"""DEGOFOOD Merchant - aplikasi merchant DEGOFOOD (Flet 0.25.2).

Satu file besar sebagai entry point `flet build apk`.
Semua data diambil dari REST API backend DEGOFOOD. Tidak ada data contoh/dummy di kode.
"""
import asyncio
import json
import os
import tempfile
import threading
import time
import traceback
import uuid
from datetime import date, datetime, timedelta

import flet as ft
import httpx

# BARIS INI DIGANTI OTOMATIS oleh build_apk.ps1 (-ApiUrl). Format harus persis:
API_BASE_URL = 'https://degofood.my.id'

BASE_KEY = 'DEGOFOOD_MERCHANT_base'
SESSION_KEY = 'DEGOFOOD_MERCHANT_session'
CURSOR_KEY = 'DEGOFOOD_MERCHANT_cursors'

BG = '#070B14'
CARD = '#0E1626'
CARD2 = '#111B2E'
BORDER = '#1E2C45'
GOLD = '#E9C46A'
GOLD_DARK = '#8A6E2E'
EMER = '#2EC4A6'
TXT = '#F4F7FB'
DIM = '#8FA0B8'
RED = '#E5646E'
GOLD_SOFT = '#2A2413'
EMER_SOFT = '#10302B'
RED_SOFT = '#331A1F'
BLUE_SOFT = '#16233A'

STATUS_LABEL = {
    'pending': 'Menunggu',
    'waiting': 'Menunggu',
    'menunggu': 'Menunggu',
    'confirmed': 'Dikonfirmasi',
    'accepted': 'Diterima',
    'diterima': 'Diterima',
    'preparing': 'Disiapkan',
    'cooking': 'Dimasak',
    'ready': 'Siap',
    'on_delivery': 'Diantar',
    'delivering': 'Diantar',
    'diantar': 'Diantar',
    'completed': 'Selesai',
    'selesai': 'Selesai',
    'cancelled': 'Dibatalkan',
    'canceled': 'Dibatalkan',
    'dibatalkan': 'Dibatalkan',
    'rejected': 'Ditolak',
    'ditolak': 'Ditolak',
}
STATUS_TONE = {
    'pending': (GOLD, GOLD_SOFT),
    'waiting': (GOLD, GOLD_SOFT),
    'menunggu': (GOLD, GOLD_SOFT),
    'confirmed': (EMER, EMER_SOFT),
    'accepted': (EMER, EMER_SOFT),
    'diterima': (EMER, EMER_SOFT),
    'preparing': (EMER, EMER_SOFT),
    'cooking': (EMER, EMER_SOFT),
    'ready': (EMER, EMER_SOFT),
    'on_delivery': (GOLD, GOLD_SOFT),
    'delivering': (GOLD, GOLD_SOFT),
    'diantar': (GOLD, GOLD_SOFT),
    'completed': (EMER, EMER_SOFT),
    'selesai': (EMER, EMER_SOFT),
    'cancelled': (RED, RED_SOFT),
    'canceled': (RED, RED_SOFT),
    'dibatalkan': (RED, RED_SOFT),
    'rejected': (RED, RED_SOFT),
    'ditolak': (RED, RED_SOFT),
}
LEDGER_LABEL = {
    'order': 'Pesanan',
    'order_credit': 'Kredit pesanan',
    'settlement': 'Settlement',
    'withdrawal': 'Pencairan',
    'withdrawal_hold': 'Ditahan pengajuan',
    'withdrawal_refund': 'Pengembalian dana',
    'fee': 'Biaya',
    'commission': 'Komisi',
    'adjustment': 'Penyesuaian',
}
WITHDRAW_LABEL = {
    'pending': 'Menunggu review admin',
    'approved': 'Disetujui admin',
    'rejected': 'Ditolak admin',
    'paid': 'Sudah ditransfer',
}


# --------------------------------------------------------------------------- #
# util kecil
# --------------------------------------------------------------------------- #
def rp(value):
    try:
        n = int(round(float(value or 0)))
    except Exception:
        n = 0
    sign = '-' if n < 0 else ''
    return sign + 'Rp ' + format(abs(n), ',d').replace(',', '.')


def txt(value, size=13, color=TXT, weight=ft.FontWeight.W_400, spacing=None):
    style = ft.TextStyle(letter_spacing=spacing) if spacing else None
    return ft.Text(str(value), size=size, color=color, weight=weight, style=style)


def section(label):
    return txt(str(label).upper(), size=11, color=DIM, weight=ft.FontWeight.W_600, spacing=1.4)


def card(content, padding=16, expand=False, bgcolor=CARD2):
    return ft.Container(content=content, bgcolor=bgcolor, border_radius=18,
                        border=ft.border.all(1, BORDER), padding=padding, expand=expand)


def circle_icon(icon, color=GOLD, size=40, bg=None):
    if bg is None:
        bg = GOLD_SOFT if color == GOLD else (EMER_SOFT if color == EMER else (RED_SOFT if color == RED else BLUE_SOFT))
    return ft.Container(width=size, height=size, border_radius=size / 2, bgcolor=bg,
                        alignment=ft.alignment.center,
                        content=ft.Icon(icon, color=color, size=int(size * 0.5)))


def gradient_header(content, padding=18):
    return ft.Container(
        content=content, padding=padding,
        border_radius=ft.border_radius.only(bottom_left=24, bottom_right=24),
        gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                                   colors=['#132B4A', '#0B1524']))


def field(label, **kw):
    kw.setdefault('hint_text', label)
    kw.setdefault('bgcolor', CARD2)
    kw.setdefault('border_radius', 14)
    return ft.TextField(color=TXT, border_color=BORDER, focused_border_color=GOLD,
                        cursor_color=GOLD, hint_style=ft.TextStyle(color=DIM, size=13),
                        label_style=ft.TextStyle(color=DIM, size=13), text_size=14, **kw)


def gold_button(label, on_click, icon=None, disabled=False, expand=False, outline=False):
    content = None
    if icon is not None:
        content = ft.Row([ft.Icon(icon, size=18, color='#0B1524' if not outline else GOLD),
                          txt(label, size=14, color='#0B1524' if not outline else GOLD, weight=ft.FontWeight.W_600)],
                         alignment=ft.MainAxisAlignment.CENTER, spacing=8, tight=True)
    btn = ft.ElevatedButton(
        text=None if content is not None else label,
        content=content,
        on_click=on_click,
        disabled=disabled,
        expand=expand,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=None if outline else GOLD,
            color=GOLD if outline else '#0B1524',
            elevation=0,
            side=ft.BorderSide(1, GOLD) if outline else None,
            shape=ft.RoundedRectangleBorder(radius=14),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ))
    return btn


def status_badge(status):
    key = str(status or '').lower()
    label = STATUS_LABEL.get(key, str(status or '-').replace('_', ' ').title())
    color, bg = STATUS_TONE.get(key, (DIM, BLUE_SOFT))
    return ft.Container(content=txt(label, size=11, color=color, weight=ft.FontWeight.W_600),
                        bgcolor=bg, border_radius=ft.border_radius.all(9),
                        border=ft.border.all(1, color),
                        padding=ft.padding.symmetric(horizontal=10, vertical=4))


def fmt_dt(value):
    if not value:
        return '-'
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(value)[:16]


def is_cancel_status(status):
    return 'cancel' in str(status or '').lower() or 'batal' in str(status or '').lower()


def unwrap_stored(raw):
    """Buka nilai client_storage yang terbungkus JSON berlapis.

    Flet web menyimpan nilai sebagai JSON, dan nilai yang dikirim sebagai string
    JSON bisa tersimpan dua kali (mis. '"\\"https://x\\""'). Tanpa dibuka berulang,
    alamat server/sesi yang tersimpan akan ditolak dan aplikasi diam-diam kembali
    ke alamat bawaan setiap kali dibuka.
    """
    value = raw
    for _ in range(3):
        if isinstance(value, str):
            s = value.strip()
            if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == '{' and s[-1] == '}')):
                try:
                    value = json.loads(s)
                    continue
                except Exception:
                    return value
        break
    return value


def resolve_base(page):
    """Ambil alamat server tersimpan; abaikan kalau bukan https/localhost (bug IP LAN)."""
    try:
        stored = unwrap_stored(page.client_storage.get(BASE_KEY))
    except Exception:
        stored = None
    if isinstance(stored, str) and stored.strip():
        s = stored.strip().strip('"').rstrip('/')
        if s.startswith('https://') or s.startswith('http://localhost') or s.startswith('http://127.0.0.1'):
            return s
    return API_BASE_URL


def safe(page, handler):
    def wrapper(e):
        try:
            handler(e)
        except ApiError as ex:
            try:
                page.open(ft.SnackBar(content=ft.Text(str(ex)), bgcolor=RED_SOFT))
            except Exception:
                traceback.print_exc()
        except Exception as ex:
            traceback.print_exc()
            try:
                page.open(ft.SnackBar(content=ft.Text(f'Error: {ex}'), bgcolor=RED_SOFT))
            except Exception:
                pass
    return wrapper


# --------------------------------------------------------------------------- #
# API client
# --------------------------------------------------------------------------- #
class ApiError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class Api:
    def __init__(self):
        self.base = API_BASE_URL
        self.token = None
        self._client = httpx.Client(timeout=25.0, follow_redirects=True)

    def set_base(self, base):
        self.base = (base or API_BASE_URL).rstrip('/')

    def _headers(self):
        h = {'Accept': 'application/json'}
        if self.token:
            h['Authorization'] = 'Bearer ' + self.token
        return h

    @staticmethod
    def _message(r):
        data = None
        try:
            data = r.json()
        except Exception:
            data = None
        if isinstance(data, dict):
            for key in ('detail', 'message', 'error'):
                v = data.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
                if isinstance(v, list) and v:
                    first = v[0]
                    if isinstance(first, dict) and first.get('msg'):
                        return str(first['msg'])
                    if isinstance(first, str):
                        return first
        body = (r.text or '').strip()
        if body:
            return body[:300]
        return f'HTTP {r.status_code}'

    def request(self, method, path, **kw):
        url = self.base + path
        try:
            r = self._client.request(method, url, headers=self._headers(), **kw)
        except httpx.HTTPError as ex:
            raise ApiError(f'Tidak bisa menghubungi server ({ex.__class__.__name__}). Periksa koneksi atau alamat server.') from None
        if r.status_code == 401 and not path.endswith('/auth/login'):
            raise ApiError('Sesi berakhir. Silakan masuk kembali.', 401)
        if r.status_code >= 400:
            raise ApiError(self._message(r), r.status_code)
        return r

    def get_json(self, path, **params):
        p = {k: v for k, v in params.items() if v not in (None, '')}
        r = self.request('GET', path, params=p or None)
        if not r.content:
            return None
        try:
            return r.json()
        except Exception:
            return None

    def post_json(self, path, body=None):
        r = self.request('POST', path, json=body if body is not None else {})
        if not r.content:
            return None
        try:
            return r.json()
        except Exception:
            return None

    def put_json(self, path, body=None):
        r = self.request('PUT', path, json=body if body is not None else {})
        if not r.content:
            return None
        try:
            return r.json()
        except Exception:
            return None

    def delete(self, path):
        r = self.request('DELETE', path)
        if not r.content:
            return None
        try:
            return r.json()
        except Exception:
            return None


# --------------------------------------------------------------------------- #
# aplikasi
# --------------------------------------------------------------------------- #
class MerchantApp:
    def __init__(self, page):
        self.page = page
        self.api = Api()
        self.api.set_base(resolve_base(page))
        self.account = None
        self.restaurant = None
        self.profile = None
        self.notif_items = []
        self.notif_note = ''
        self.cursors = self._load_cursors()
        self.polling = False
        self.dlg = None
        self.orders_filter = 'aktif'
        self.menus_q = ''
        self.menus_cat = ''
        self.fin_tab = 0
        self.fin_data = None
        self._notif_ref = ft.Ref[ft.Column]()

    # ---------------- util ----------------
    def safe(self, handler):
        return safe(self.page, handler)

    def snack(self, message, bgcolor=CARD2):
        try:
            self.page.open(ft.SnackBar(content=ft.Text(str(message)), bgcolor=bgcolor))
        except Exception:
            traceback.print_exc()

    def set_fab(self, control):
        try:
            self.page.floating_action_button = control
            if control is not None:
                self.page.floating_action_button_location = ft.FloatingActionButtonLocation.END_FLOAT
            self.page.update()
        except Exception:
            pass

    def open_dialog(self, dialog):
        self.dlg = dialog
        try:
            self.page.open(dialog)
        except Exception:
            traceback.print_exc()

    def close_dialog(self, e=None):
        try:
            if self.dlg is not None:
                self.page.close(self.dlg)
                self.dlg = None
        except Exception:
            traceback.print_exc()

    def loading_view(self, message='Memuat...'):
        return ft.Container(expand=True, alignment=ft.alignment.center,
                            content=ft.Column([
                                ft.ProgressRing(width=32, height=32, stroke_width=3, color=GOLD),
                                txt(message, size=13, color=DIM),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                                alignment=ft.MainAxisAlignment.CENTER))

    def error_view(self, message, retry_handler):
        return ft.Container(expand=True, padding=24, alignment=ft.alignment.center,
                            content=ft.Column([
                                circle_icon(ft.Icons.CLOUD_OFF_ROUNDED, RED, 56),
                                txt('Gagal memuat data', size=16, weight=ft.FontWeight.W_600),
                                txt(message, size=13, color=DIM),
                                gold_button('Coba lagi', self.safe(retry_handler), icon=ft.Icons.REFRESH),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                                alignment=ft.MainAxisAlignment.CENTER))

    def empty_view(self, message, icon=ft.Icons.INBOX_ROUNDED):
        return ft.Container(padding=ft.padding.symmetric(vertical=40),
                            content=ft.Column([
                                circle_icon(icon, DIM, 52, BLUE_SOFT),
                                txt(message, size=13, color=DIM),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12))

    def set_view(self, control, tab_index=None, show_nav=True, fab=None):
        self.body.content = control
        self.nav.visible = show_nav
        if tab_index is not None:
            self.navbar.selected_index = tab_index
        self.set_fab(fab)
        try:
            self.page.update()
        except Exception:
            traceback.print_exc()

    # ---------------- storage ----------------
    def load_session(self):
        try:
            raw = unwrap_stored(self.page.client_storage.get(SESSION_KEY))
        except Exception:
            return None
        if not raw:
            return None
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def save_session(self):
        payload = {'token': self.api.token, 'account': self.account, 'base': self.api.base}
        try:
            self.page.client_storage.set(SESSION_KEY, json.dumps(payload))
        except Exception:
            traceback.print_exc()

    def clear_session(self):
        for key in (SESSION_KEY,):
            try:
                self.page.client_storage.remove(key)
            except Exception:
                pass
        self.api.token = None
        self.account = None

    def _load_cursors(self):
        try:
            raw = unwrap_stored(self.page.client_storage.get(CURSOR_KEY))
            if raw:
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, dict):
                    return {'order': int(data.get('order') or 0), 'event': int(data.get('event') or 0)}
        except Exception:
            pass
        return {'order': 0, 'event': 0}

    def _save_cursors(self):
        try:
            self.page.client_storage.set(CURSOR_KEY, json.dumps(self.cursors))
        except Exception:
            pass

    # ---------------- shell ----------------
    def build_shell(self):
        self.body = ft.Container(expand=True, bgcolor=BG)
        self.navbar = ft.NavigationBar(
            selected_index=0,
            bgcolor=CARD,
            on_change=self.safe(self.on_nav),
            indicator_color=ft.Colors.with_opacity(0.18, GOLD),
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
            destinations=[
                ft.NavigationDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label='Beranda'),
                ft.NavigationDestination(icon=ft.Icons.RECEIPT_LONG_OUTLINED, selected_icon=ft.Icons.RECEIPT_LONG, label='Pesanan'),
                ft.NavigationDestination(icon=ft.Icons.RESTAURANT_MENU_OUTLINED, selected_icon=ft.Icons.RESTAURANT_MENU, label='Menu'),
                ft.NavigationDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET, label='Keuangan'),
                ft.NavigationDestination(icon=ft.Icons.GRID_VIEW_OUTLINED, selected_icon=ft.Icons.GRID_VIEW, label='Lainnya'),
            ])
        self.nav = ft.Container(content=self.navbar)
        root = ft.Column(expand=True, spacing=0, controls=[self.body, self.nav])
        self.page.add(root)

    def on_nav(self, e):
        idx = int(e.control.selected_index)
        if idx == 0:
            self.show_home()
        elif idx == 1:
            self.show_orders()
        elif idx == 2:
            self.show_menus()
        elif idx == 3:
            self.show_finance()
        else:
            self.show_more()

    # ---------------- start / login ----------------
    def start(self):
        try:
            if not self.page.client_storage.get(BASE_KEY):
                self.page.client_storage.set(BASE_KEY, API_BASE_URL)
        except Exception:
            pass
        self.build_shell()
        self.set_view(self.loading_view('Menyiapkan aplikasi...'), show_nav=False)
        # Di Flet web, client_storage kadang belum terisi pada pembacaan pertama
        # (dibaca sebelum penyimpanan selesai dimuat). Coba beberapa kali sebelum
        # menyimpulkan "belum login", supaya sesi tersimpan tidak hilang tiap dibuka.
        session = None
        for attempt in range(5):
            session = self.load_session()
            if session and session.get('token'):
                break
            if attempt < 4:
                time.sleep(0.4)
        if not session or not session.get('token'):
            self.show_login()
            return
        self.api.token = session.get('token')
        self.account = session.get('account') or {}
        try:
            acc = self.api.get_json('/api/merchant/me')
            if acc:
                self.account = acc
            self.enter_app()
        except ApiError as ex:
            if ex.status == 401:
                self.clear_session()
                self.show_login()
                self.snack('Sesi berakhir, silakan masuk kembali.')
            else:
                self.snack(f'Gagal memuat profil terbaru: {ex}')
                self.enter_app()
        except Exception as ex:
            traceback.print_exc()
            self.snack(f'Gagal memulai: {ex}')
            self.show_login()

    # ---------------- pendaftaran mandiri ----------------
    def show_register(self):
        self.set_view(self.register_view(), show_nav=False)

    def register_view(self):
        """Layar pendaftaran: merchant mengisi sendiri HP/email + password pilihannya."""
        self.reg_name = field('Nama pemilik / penanggung jawab', prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED)
        self.reg_phone = field('Nomor HP (08xx / +62xx)', prefix_icon=ft.Icons.PHONE_ROUNDED,
                               keyboard_type=ft.KeyboardType.PHONE)
        self.reg_email = field('Email (opsional kalau sudah isi nomor HP)',
                               prefix_icon=ft.Icons.MAIL_OUTLINE_ROUNDED)
        self.reg_store = field('Nama toko / warung', prefix_icon=ft.Icons.STOREFRONT_ROUNDED)
        self.reg_address = field('Alamat toko', prefix_icon=ft.Icons.PLACE_OUTLINED, multiline=True,
                                 min_lines=2, max_lines=3)
        self.reg_pwd = field('Password (min 8 karakter, ada huruf & angka)', password=True,
                             can_reveal_password=True, prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED)
        self.reg_pwd2 = field('Ulangi password', password=True, can_reveal_password=True,
                              prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED)
        self.reg_err = txt('', size=12, color=RED)
        self.reg_err.visible = False
        self.reg_ok = txt('', size=12, color=EMER)
        self.reg_ok.visible = False
        self.reg_btn = gold_button('Kirim pendaftaran', self.safe(self.register_click),
                                   icon=ft.Icons.SEND_ROUNDED, expand=True)

        form = card(ft.Column([
            section('Daftar jadi merchant'),
            txt('Isi data toko Anda. Nomor HP atau email minimal salah satu. '
                'Setelah dikirim, akun BELUM aktif: admin DEGOFOOD memverifikasi dulu '
                'dan menautkan restoran Anda sebelum bisa masuk.', size=11, color=DIM),
            self.reg_name,
            self.reg_phone,
            self.reg_email,
            self.reg_store,
            self.reg_address,
            self.reg_pwd,
            self.reg_pwd2,
            self.reg_err,
            self.reg_ok,
            self.reg_btn,
            ft.TextButton(content=txt('Sudah punya akun? Masuk', size=12, color=GOLD),
                          on_click=self.safe(lambda e: self.show_login())),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))

        header = ft.Container(
            content=ft.Column([
                ft.Container(width=64, height=64, border_radius=32, bgcolor=GOLD_SOFT,
                             alignment=ft.alignment.center, border=ft.border.all(1, GOLD),
                             content=ft.Icon(ft.Icons.PERSON_ADD_ALT_ROUNDED, color=GOLD, size=30)),
                txt('Pendaftaran Merchant', size=18, weight=ft.FontWeight.BOLD),
                txt('DEGOFOOD', size=12, color=DIM, spacing=3),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            padding=ft.padding.only(top=40, bottom=18))

        return ft.Container(
            expand=True,
            gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                                       colors=['#0B1524', '#070B14']),
            content=ft.Column([
                header,
                ft.Container(content=form, padding=ft.padding.symmetric(horizontal=20)),
                ft.Container(height=18),
                ft.TextButton(content=txt('Alamat server: ' + self.api.base, size=11, color=DIM),
                              on_click=self.safe(lambda e: self.show_server_page(back_to_login=True))),
            ], expand=True, scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=0))

    def register_click(self, e):
        nama = (self.reg_name.value or '').strip()
        phone = (self.reg_phone.value or '').strip()
        email = (self.reg_email.value or '').strip()
        toko = (self.reg_store.value or '').strip()
        alamat = (self.reg_address.value or '').strip()
        pwd = self.reg_pwd.value or ''
        pwd2 = self.reg_pwd2.value or ''

        def gagal(pesan):
            self.reg_err.value = pesan
            self.reg_err.visible = True
            self.page.update()

        if len(nama) < 2:
            return gagal('Nama pemilik wajib diisi (minimal 2 karakter).')
        if not phone and not email:
            return gagal('Isi nomor HP atau email (minimal salah satu).')
        if len(pwd) < 8:
            return gagal('Password minimal 8 karakter.')
        if pwd != pwd2:
            return gagal('Password dan ulangi password tidak sama.')

        self.reg_err.visible = False
        self.reg_ok.visible = False
        self.reg_btn.disabled = True
        self.reg_btn.content = ft.Row([
            ft.ProgressRing(width=16, height=16, stroke_width=2, color='#0B1524'),
            txt('Mengirim...', size=14, color='#0B1524', weight=ft.FontWeight.W_600),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=8, tight=True)
        self.page.update()
        try:
            body = {'name': nama, 'password': pwd}
            if phone:
                body['phone'] = phone
            if email:
                body['email'] = email
            if toko:
                body['store_name'] = toko
            if alamat:
                body['address'] = alamat
            data = self.api.post_json('/api/merchant/auth/register', body) or {}
            self.reg_ok.value = (data.get('message')
                                 or 'Pendaftaran diterima. Tunggu verifikasi admin DEGOFOOD.')
            self.reg_ok.visible = True
            for f in (self.reg_pwd, self.reg_pwd2):
                f.value = ''
            self.page.update()
        except ApiError as ex:
            self.reg_err.value = str(ex)
            self.reg_err.visible = True
        finally:
            self.reg_btn.disabled = False
            self.reg_btn.content = None
            self.reg_btn.text = 'Kirim pendaftaran'
            try:
                self.page.update()
            except Exception:
                pass

    def enter_app(self):
        self.restaurant = (self.account or {}).get('restaurant') or {}
        self.show_home()

    def show_login(self):
        self.set_view(self.login_view(), show_nav=False)

    def login_view(self):
        self.login_ident = field('Nomor HP atau Email', autofocus=True,
                                 prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED)
        self.login_pwd = field('Password', password=True, can_reveal_password=True,
                               prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
                               on_submit=self.safe(self.login_click))
        self.login_err = txt('', size=12, color=RED)
        self.login_err.visible = False
        self.login_btn = gold_button('Masuk', self.safe(self.login_click), icon=ft.Icons.LOGIN_ROUNDED, expand=True)

        header = ft.Container(
            content=ft.Column([
                ft.Container(width=72, height=72, border_radius=36, bgcolor=GOLD_SOFT,
                             alignment=ft.alignment.center,
                             border=ft.border.all(1, GOLD),
                             content=ft.Icon(ft.Icons.STOREFRONT_ROUNDED, color=GOLD, size=34)),
                txt('DEGOFOOD', size=26, weight=ft.FontWeight.BOLD, color=GOLD, spacing=3),
                txt('Merchant', size=13, color=DIM, spacing=2),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            padding=ft.padding.only(top=60, bottom=26))

        form = card(ft.Column([
            section('Masuk ke akun toko'),
            self.login_ident,
            self.login_pwd,
            self.login_err,
            self.login_btn,
            txt('Belum punya akun? Daftar sendiri dari aplikasi ini, lalu tunggu verifikasi admin.',
                size=11, color=DIM),
            ft.TextButton(content=txt('Daftar jadi merchant', size=12, color=GOLD),
                          on_click=self.safe(lambda e: self.show_register())),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))

        footer = ft.Column([
            txt('Versi aplikasi merchant 1.0.0', size=11, color=DIM),
            ft.TextButton(content=txt('Alamat server: ' + self.api.base, size=11, color=DIM),
                          on_click=self.safe(lambda e: self.show_server_page(back_to_login=True))),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

        return ft.Container(
            expand=True,
            gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                                       colors=['#0B1524', '#070B14']),
            content=ft.Column([
                header,
                ft.Container(content=form, padding=ft.padding.symmetric(horizontal=20)),
                ft.Container(height=18),
                footer,
            ], expand=True, scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=0))

    def login_click(self, e):
        ident = (self.login_ident.value or '').strip()
        pwd = self.login_pwd.value or ''
        if not ident or not pwd:
            self.login_err.value = 'Nomor HP/email dan password wajib diisi.'
            self.login_err.visible = True
            self.page.update()
            return
        self.login_btn.disabled = True
        self.login_err.visible = False
        self.login_btn.content = ft.Row([
            ft.ProgressRing(width=16, height=16, stroke_width=2, color='#0B1524'),
            txt('Memproses...', size=14, color='#0B1524', weight=ft.FontWeight.W_600),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=8, tight=True)
        self.page.update()
        try:
            data = self.api.post_json('/api/merchant/auth/login',
                                      {'identifier': ident, 'password': pwd})
            if not data or not data.get('token'):
                raise ApiError('Server tidak mengirim token. Coba lagi.')
            self.api.token = data.get('token')
            self.account = data.get('account') or {}
            self.save_session()
            self.login_pwd.value = ''
            self.enter_app()
        except ApiError as ex:
            self.login_err.value = str(ex)
            self.login_err.visible = True
        finally:
            self.login_btn.disabled = False
            self.login_btn.content = None
            self.login_btn.text = 'Masuk'
            try:
                self.page.update()
            except Exception:
                pass

    def logout_click(self, e):
        try:
            self.api.post_json('/api/merchant/auth/logout')
        except Exception:
            pass
        self.stop_polling()
        self.clear_session()
        self.show_login()
        self.snack('Anda telah keluar.')

    # ---------------- BERANDA ----------------
    def show_home(self, e=None):
        self.set_view(self.loading_view('Memuat beranda...'), tab_index=0, fab=None)
        try:
            data = self.api.get_json('/api/merchant/dashboard') or {}
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), self.show_home), tab_index=0)
            return
        self.dashboard = data
        rest = data.get('restaurant') or self.restaurant or {}
        self.restaurant = rest
        stats = data.get('stats') or {}
        balance = data.get('balance') or {}
        series = data.get('series') or []
        top_menus = data.get('top_menus') or []
        is_open = bool(rest.get('is_open'))

        header = gradient_header(ft.Column([
            ft.Row([
                ft.Column([
                    section('Toko Anda'),
                    txt(rest.get('name') or (self.account or {}).get('name') or 'Toko', size=20,
                        weight=ft.FontWeight.BOLD),
                ], spacing=2, expand=True),
                ft.Container(content=txt('BUKA' if is_open else 'TUTUP', size=11,
                                         color=EMER if is_open else RED, weight=ft.FontWeight.W_600),
                             bgcolor=EMER_SOFT if is_open else RED_SOFT, border_radius=ft.border_radius.all(10),
                             border=ft.border.all(1, EMER if is_open else RED),
                             padding=ft.padding.symmetric(horizontal=12, vertical=6)),
            ], vertical_alignment=ft.VerticalAlignment.CENTER),
            ft.Container(height=4),
            ft.Row([
                gold_button('Tutup Toko' if is_open else 'Buka Toko',
                            self.safe(lambda ev: self.toggle_open(not is_open)),
                            icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED, outline=True, expand=True),
                gold_button('Segarkan', self.safe(self.show_home),
                            icon=ft.Icons.REFRESH_ROUNDED, expand=True),
            ], spacing=10),
        ], spacing=8))

        stat_cards = ft.Column([
            ft.Row([
                self.stat_card(ft.Icons.RECEIPT_LONG_ROUNDED, 'Pesanan hari ini', str(int(stats.get('today_orders') or 0)), GOLD),
                self.stat_card(ft.Icons.PAYMENTS_ROUNDED, 'Pendapatan hari ini', rp(stats.get('today_revenue')), EMER),
            ], spacing=12),
            ft.Row([
                self.stat_card(ft.Icons.PENDING_ACTIONS_ROUNDED, 'Pesanan aktif', str(int(stats.get('active_orders') or 0)), GOLD),
                self.stat_card(ft.Icons.MENU_BOOK_ROUNDED, 'Menu aktif', str(int(stats.get('active_menus') or 0)), EMER),
            ], spacing=12),
        ], spacing=12)

        top_items = []
        for i, m in enumerate(top_menus[:5], start=1):
            top_items.append(ft.Row([
                circle_icon(ft.Icons.EMOJI_EVENTS_ROUNDED, GOLD, 34),
                ft.Column([
                    txt(m.get('name') or '-', size=13, weight=ft.FontWeight.W_600),
                    txt(f"{int(m.get('quantity') or 0)} terjual", size=11, color=DIM),
                ], spacing=1, expand=True),
                txt(rp(m.get('revenue')), size=13, color=GOLD, weight=ft.FontWeight.W_600),
            ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=12))
        if not top_items:
            top_items = [txt('Belum ada penjualan tercatat.', size=12, color=DIM)]

        bal_card = card(ft.Column([
            section('Saldo tersedia'),
            txt(rp(balance.get('available_balance')), size=30, color=GOLD, weight=ft.FontWeight.BOLD),
            ft.Row([
                txt(f"Settlement menunggu: {int(balance.get('settlements_pending') or 0)}", size=12, color=DIM),
                txt(f"Disetujui: {int(balance.get('settlements_approved') or 0)}", size=12, color=DIM),
            ], spacing=14),
            txt(balance.get('note') or 'Saldo bertambah setelah admin memverifikasi settlement tiap pesanan.',
                size=11, color=DIM),
            ft.TextButton(content=txt('Lihat keuangan', size=12, color=GOLD),
                          on_click=self.safe(lambda ev: self.show_finance())),
        ], spacing=6))

        content = ft.ListView(expand=True, spacing=12, padding=ft.padding.all(16), controls=[
            header,
            stat_cards,
            card(self.bar_chart(series), padding=16),
            card(ft.Column([section('5 menu terlaris')] + top_items, spacing=12)),
            bal_card,
            ft.Container(height=8),
        ])
        self.set_view(ft.Container(expand=True, content=content), tab_index=0)

    def on_home_refresh(self, e):
        self.show_home()

    def stat_card(self, icon, label, value, color):
        return card(ft.Column([
            ft.Row([circle_icon(icon, color, 38), txt(label, size=11, color=DIM)], spacing=10),
            txt(value, size=20, color=color if color == GOLD else TXT, weight=ft.FontWeight.BOLD),
        ], spacing=10), expand=True)

    def bar_chart(self, series):
        if not series:
            return ft.Column([section('Pendapatan 7 hari'), txt('Belum ada data.', size=12, color=DIM)], spacing=8)
        values = [float(s.get('revenue') or 0) for s in series]
        mx = max(values + [1.0])
        bars = []
        for s in series:
            rev = float(s.get('revenue') or 0)
            h = max(6, int(120 * rev / mx))
            d = str(s.get('date') or '')
            label = f'{d[8:10]}/{d[5:7]}' if len(d) >= 10 else d
            bars.append(ft.Column([
                ft.Container(width=24, height=h, border_radius=ft.border_radius.only(top_left=7, top_right=7),
                             gradient=ft.LinearGradient(begin=ft.alignment.bottom_center,
                                                        end=ft.alignment.top_center,
                                                        colors=[GOLD, GOLD_DARK]),
                             tooltip=rp(rev)),
                txt(label, size=9, color=DIM),
                txt(str(int(s.get('orders') or 0)), size=9, color=DIM),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3,
                alignment=ft.MainAxisAlignment.END, expand=True))
        return ft.Column([
            section('Pendapatan 7 hari'),
            txt(f'Tertinggi: {rp(mx)}', size=11, color=DIM),
            ft.Container(height=140, content=ft.Row(bars, spacing=6,
                                                    vertical_alignment=ft.CrossAxisAlignment.END)),
        ], spacing=8)

    def toggle_open(self, value):
        try:
            prof = self.api.get_json('/api/merchant/profile') or {}
        except ApiError as ex:
            self.snack(str(ex))
            return
        body = {
            'description': prof.get('description') or '',
            'open_time': prof.get('open_time') or '',
            'close_time': prof.get('close_time') or '',
            'min_order': prof.get('min_order') or 0,
            'is_accepting_orders': prof.get('is_accepting_orders', True),
            'is_open': bool(value),
        }
        try:
            self.api.put_json('/api/merchant/profile', body)
            self.snack('Toko sekarang ' + ('BUKA' if value else 'TUTUP'), EMER_SOFT if value else RED_SOFT)
            self.show_home()
        except ApiError as ex:
            self.snack(str(ex), RED_SOFT)

    # ---------------- PESANAN ----------------
    def show_orders(self, e=None):
        self.set_view(self.loading_view('Memuat pesanan...'), tab_index=1, fab=None)
        try:
            params = {'limit': 100}
            if self.orders_filter != 'semua':
                params['status'] = self.orders_filter
            orders = self.api.get_json('/api/merchant/orders', **params) or []
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), self.show_orders), tab_index=1)
            return
        chips = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
            self.filter_chip(label, key) for label, key in
            [('Aktif', 'aktif'), ('Semua', 'semua'), ('Selesai', 'selesai'), ('Dibatalkan', 'dibatalkan')]
        ])
        header = gradient_header(ft.Column([
            ft.Row([ft.Container(expand=True, content=txt('Pesanan', size=20, weight=ft.FontWeight.BOLD)),
                    ft.IconButton(icon=ft.Icons.REFRESH_ROUNDED, icon_color=GOLD,
                                  tooltip='Muat ulang', on_click=self.safe(self.show_orders))]),
            chips,
        ], spacing=8))

        if orders:
            tiles = [self.order_tile(o) for o in orders]
        else:
            tiles = [self.empty_view('Belum ada pesanan pada filter ini.', ft.Icons.RECEIPT_LONG_ROUNDED)]
        self.set_view(ft.Container(expand=True, content=ft.ListView(
            expand=True, spacing=12, padding=ft.padding.all(16), controls=[header] + tiles)),
            tab_index=1)

    def filter_chip(self, label, key):
        active = self.orders_filter == key
        return ft.Container(
            content=txt(label, size=12, color='#0B1524' if active else DIM, weight=ft.FontWeight.W_600),
            bgcolor=GOLD if active else '#0E1A2C',
            border=ft.border.all(1, GOLD if active else BORDER),
            border_radius=ft.border_radius.all(20),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            on_click=self.safe(lambda e, k=key: self.set_orders_filter(k)),
            animate_opacity=200)

    def set_orders_filter(self, key):
        self.orders_filter = key
        self.show_orders()

    def order_tile(self, o):
        items = o.get('items') or []
        n_item = sum(int(i.get('quantity') or 0) for i in items) or len(items)
        return ft.Container(
            bgcolor=CARD2, border_radius=18, border=ft.border.all(1, BORDER),
            padding=14, ink=True,
            on_click=self.safe(lambda e, oid=o.get('id'): self.show_order_detail(oid)),
            content=ft.Column([
                ft.Row([txt(f"#{o.get('id')}", size=12, color=DIM),
                        status_badge(o.get('status'))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                txt(o.get('customer_name') or 'Pelanggan', size=15, weight=ft.FontWeight.W_600),
                ft.Row([txt(fmt_dt(o.get('created_at')), size=11, color=DIM),
                        txt(f'{n_item} item', size=11, color=DIM)], spacing=12),
                ft.Row([txt('Total', size=11, color=DIM),
                        txt(rp(o.get('total_price')), size=15, color=GOLD, weight=ft.FontWeight.BOLD)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=6))

    def show_order_detail(self, order_id):
        self.set_view(self.loading_view('Memuat detail pesanan...'), tab_index=1)
        try:
            order = self.api.get_json(f'/api/merchant/orders/{order_id}') or {}
            events = self.api.get_json(f'/api/merchant/orders/{order_id}/events') or []
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), lambda e: self.show_order_detail(order_id)), tab_index=1)
            return
        if not isinstance(order, dict) or not order:
            self.set_view(self.error_view('Pesanan tidak ditemukan.', self.show_orders), tab_index=1)
            return

        items = order.get('items') or []
        item_rows = []
        for it in items:
            qty = int(it.get('quantity') or 0)
            price = float(it.get('price') or 0)
            item_rows.append(ft.Row([
                txt(f"{qty}x", size=13, color=GOLD, weight=ft.FontWeight.W_600),
                ft.Column([txt(it.get('menu_name') or '-', size=13),
                           txt(rp(price) + ' / porsi', size=11, color=DIM)], spacing=1, expand=True),
                txt(rp(price * qty), size=13, weight=ft.FontWeight.W_600),
            ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=10))
        if not item_rows:
            item_rows = [txt('Tidak ada rincian item dari server.', size=12, color=DIM)]

        phone = order.get('customer_phone') or ''
        phone_row = ft.Container(
            content=ft.Row([
                circle_icon(ft.Icons.CALL_ROUNDED, EMER, 36),
                ft.Column([txt('Telepon pelanggan', size=11, color=DIM),
                           txt(phone or '-', size=14, weight=ft.FontWeight.W_600)], spacing=1, expand=True),
                txt('Salin', size=11, color=GOLD) if phone else txt('', size=11),
            ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=10),
            on_click=self.safe(lambda e: self.copy_phone(phone)) if phone else None,
            ink=bool(phone))

        actions = []
        for st in (order.get('allowed_next_status') or []):
            label = STATUS_LABEL.get(str(st).lower(), str(st).replace('_', ' ').title())
            actions.append(gold_button(label, self.safe(lambda e, s=st: self.ask_status_change(order_id, s)),
                                       outline=is_cancel_status(st)))
        if actions:
            # JANGAN pakai expand=True di dalam ft.Row(wrap=True): Expanded di dalam Wrap
            # membuat Flutter gagal layout dan tombolnya tidak pernah tampil.
            action_block = ft.Column([section('Aksi tersedia'),
                                      ft.Row(actions, spacing=10, wrap=True, run_spacing=10)], spacing=10)
        else:
            action_block = ft.Column([section('Aksi tersedia'),
                                      txt('Tidak ada aksi lanjutan untuk status ini.', size=12, color=DIM)], spacing=8)

        timeline = []
        for ev in events:
            frm = STATUS_LABEL.get(str(ev.get('from_status') or '').lower(), ev.get('from_status') or '-')
            to = STATUS_LABEL.get(str(ev.get('to_status') or '').lower(), ev.get('to_status') or '-')
            note = ev.get('note')
            timeline.append(ft.Row([
                ft.Container(width=10, height=10, border_radius=5, bgcolor=GOLD, margin=ft.margin.only(top=5)),
                ft.Column([
                    txt(f'{frm} → {to}', size=13, weight=ft.FontWeight.W_600),
                    txt(f"{fmt_dt(ev.get('created_at'))} · {ev.get('actor') or '-'}", size=11, color=DIM),
                ] + ([txt(str(note), size=12, color=DIM)] if note else []), spacing=2, expand=True),
            ], vertical_alignment=ft.VerticalAlignment.START, spacing=12))
        if not timeline:
            timeline = [txt('Belum ada riwayat perubahan status.', size=12, color=DIM)]

        body = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[
            card(ft.Column([
                ft.Row([ft.Container(content=txt(f"Pesanan #{order.get('id')}", size=16, weight=ft.FontWeight.BOLD), expand=True),
                        status_badge(order.get('status'))], vertical_alignment=ft.VerticalAlignment.CENTER),
                txt(f"Dibuat {fmt_dt(order.get('created_at'))}", size=11, color=DIM),
                ft.Divider(color=BORDER, height=18),
                section('Rincian item'),
            ] + item_rows + [
                ft.Divider(color=BORDER, height=18),
                ft.Row([txt('Total pesanan', size=13, weight=ft.FontWeight.W_600),
                        txt(rp(order.get('total_price')), size=18, color=GOLD, weight=ft.FontWeight.BOLD)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([txt('Ongkos kirim', size=12, color=DIM),
                        txt(rp(order.get('delivery_fee')), size=12, color=DIM)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10)),
            card(ft.Column([section('Pelanggan & pengiriman'),
                            txt(order.get('customer_name') or 'Pelanggan', size=14, weight=ft.FontWeight.W_600),
                            txt(order.get('delivery_address') or 'Alamat tidak tersedia.', size=12, color=DIM),
                            txt('Catatan: ' + (str(order.get('notes')) if order.get('notes') else '-'),
                                size=12, color=DIM),
                            txt('Kurir: ' + (order.get('driver_name') or 'belum ada'), size=12, color=DIM),
                            ft.Container(height=4), phone_row], spacing=8)),
            action_block,
            card(ft.Column([section('Riwayat status')] + timeline, spacing=12)),
            ft.Container(height=8),
        ])
        self.set_view(ft.Column(expand=True, spacing=0, controls=[
            self.sub_header(f'Detail Pesanan #{order_id}', self.show_orders),
            body,
        ]), tab_index=1)

    def sub_header(self, title, on_back):
        return gradient_header(ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=TXT,
                          on_click=self.safe(on_back), tooltip='Kembali'),
            ft.Container(expand=True, content=txt(title, size=17, weight=ft.FontWeight.W_600)),
        ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=4), padding=ft.padding.only(left=6, right=16, top=8, bottom=10))

    def copy_phone(self, phone):
        if not phone:
            return
        try:
            self.page.set_clipboard(phone)
            self.snack('Nomor ' + phone + ' disalin.', EMER_SOFT)
        except Exception as ex:
            self.snack(f'Gagal menyalin: {ex}', RED_SOFT)

    def ask_status_change(self, order_id, status):
        label = STATUS_LABEL.get(str(status).lower(), str(status).replace('_', ' ').title())
        note_field = field('Catatan (opsional)', multiline=True, min_lines=2, max_lines=3)
        cancel = is_cancel_status(status)

        def do_change(e):
            body = {'status': status}
            note = (note_field.value or '').strip()
            if note:
                body['note'] = note
            self.close_dialog()
            try:
                self.api.post_json(f'/api/merchant/orders/{order_id}/status', body)
                self.snack(f'Status diubah ke {label}.', EMER_SOFT)
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)
            self.show_order_detail(order_id)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD,
            title=txt(('Batalkan pesanan?' if cancel else f'Ubah status ke {label}?'), size=16,
                      weight=ft.FontWeight.W_600),
            content=ft.Column([
                txt(('Pesanan yang dibatalkan tidak bisa dikembalikan ke alur normal.' if cancel
                     else 'Status pesanan akan diubah dan pelanggan melihat perubahan ini.'), size=12, color=DIM),
                note_field,
            ], spacing=12, tight=True, width=320),
            actions=[
                ft.TextButton(content=txt('Batal', size=13, color=DIM), on_click=self.safe(lambda e: self.close_dialog())),
                gold_button('Ya, lanjutkan', self.safe(do_change), expand=False),
            ])
        self.open_dialog(dlg)

    # ---------------- MENU ----------------
    def show_menus(self, e=None):
        self.set_view(self.loading_view('Memuat menu...'), tab_index=2,
                      fab=ft.FloatingActionButton(
                          icon=ft.Icons.ADD_ROUNDED, bgcolor=GOLD, foreground_color='#0B1524',
                          tooltip='Tambah menu', on_click=self.safe(lambda ev: self.menu_form(None))))
        try:
            menus = self.api.get_json('/api/merchant/menus', q=self.menus_q, category=self.menus_cat) or []
            cats = (self.api.get_json('/api/merchant/menu-categories') or {}).get('categories') or []
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), self.show_menus), tab_index=2)
            return

        self.menu_search = field('Cari nama menu...', value=self.menus_q,
                                 on_submit=self.safe(lambda ev: self.apply_menu_search()))
        self.menu_search.on_change = self.safe(lambda ev: None)
        cat_options = [ft.dropdown.Option(key='', text='Semua kategori')]
        for c in cats:
            if isinstance(c, dict):
                name = c.get('name') or c.get('category') or c.get('slug')
                key = c.get('slug') or c.get('name') or name
            else:
                name = key = str(c)
            cat_options.append(ft.dropdown.Option(key=str(key), text=str(name)))
        self.menu_cat_dd = ft.Dropdown(
            options=cat_options, value=self.menus_cat if self.menus_cat else '',
            bgcolor=CARD2, border_color=BORDER, focused_border_color=GOLD, color=TXT,
            border_radius=14, text_size=13, on_change=self.safe(lambda ev: self.apply_menu_filter()))

        header = gradient_header(ft.Column([
            ft.Row([ft.Container(expand=True, content=txt('Menu', size=20, weight=ft.FontWeight.BOLD)),
                    ft.IconButton(icon=ft.Icons.ADD_ROUNDED, icon_color=GOLD, tooltip='Tambah menu',
                                  on_click=self.safe(lambda ev: self.menu_form(None)))]),
            ft.Row([
                ft.Container(content=self.menu_search, expand=True),
                ft.IconButton(icon=ft.Icons.SEARCH_ROUNDED, icon_color=GOLD,
                              on_click=self.safe(lambda ev: self.apply_menu_search())),
            ], vertical_alignment=ft.VerticalAlignment.CENTER),
            self.menu_cat_dd,
        ], spacing=8))

        tiles = [self.menu_tile(m) for m in menus] or \
            [self.empty_view('Belum ada menu. Tekan tombol + untuk menambah.', ft.Icons.RESTAURANT_MENU_ROUNDED)]
        self.set_view(ft.Container(expand=True, content=ft.ListView(
            expand=True, spacing=12, padding=ft.padding.all(16), controls=[header] + tiles)),
            tab_index=2,
            fab=ft.FloatingActionButton(icon=ft.Icons.ADD_ROUNDED, bgcolor=GOLD, foreground_color='#0B1524',
                                        tooltip='Tambah menu',
                                        on_click=self.safe(lambda ev: self.menu_form(None))))

    def apply_menu_search(self):
        self.menus_q = (self.menu_search.value or '').strip()
        self.show_menus()

    def apply_menu_filter(self):
        self.menus_cat = self.menu_cat_dd.value or ''
        self.show_menus()

    def menu_tile(self, m):
        img = (m.get('image_url') or '').strip()
        if img:
            thumb = ft.Container(width=64, height=64, border_radius=14,
                                 clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                 content=ft.Image(src=img, width=64, height=64, fit=ft.ImageFit.COVER,
                                                  error_content=ft.Icon(ft.Icons.RESTAURANT_ROUNDED,
                                                                        color=DIM, size=26)))
        else:
            thumb = circle_icon(ft.Icons.RESTAURANT_ROUNDED, GOLD, 56)
        available = bool(m.get('is_available'))
        stock = m.get('stock')
        badges = []
        if not available:
            badges.append(ft.Container(content=txt('Habis', size=10, color=RED, weight=ft.FontWeight.W_600),
                                       bgcolor=RED_SOFT, border_radius=ft.border_radius.all(8),
                                       border=ft.border.all(1, RED),
                                       padding=ft.padding.symmetric(horizontal=8, vertical=3)))
        if stock is not None:
            badges.append(ft.Container(content=txt(f'Stok {int(stock)}', size=10, color=DIM),
                                       bgcolor=BLUE_SOFT, border_radius=ft.border_radius.all(8),
                                       padding=ft.padding.symmetric(horizontal=8, vertical=3)))
        return ft.Container(
            bgcolor=CARD2, border_radius=18, border=ft.border.all(1, BORDER), padding=14, ink=True,
            on_click=self.safe(lambda e, mid=m.get('id'): self.menu_form(mid)),
            content=ft.Row([
                thumb,
                ft.Column([
                    txt(m.get('name') or '-', size=14, weight=ft.FontWeight.W_600),
                    txt((m.get('category') or 'tanpa kategori'), size=11, color=DIM),
                    ft.Row([txt(rp(m.get('price')), size=14, color=GOLD, weight=ft.FontWeight.BOLD)] + badges,
                           spacing=8, wrap=True),
                ], spacing=4, expand=True),
                ft.IconButton(icon=ft.Icons.TOGGLE_ON_ROUNDED if available else ft.Icons.TOGGLE_OFF_ROUNDED,
                              icon_color=EMER if available else DIM, tooltip='Ubah ketersediaan',
                              on_click=self.safe(lambda e, mm=dict(m): self.quick_toggle_menu(mm))),
            ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=12))

    def quick_toggle_menu(self, m):
        body = {
            'name': m.get('name') or '',
            'description': m.get('description') or '',
            'price': m.get('price') or 0,
            'is_available': not bool(m.get('is_available')),
            'category': m.get('category') or '',
            'image_url': m.get('image_url') or '',
            'stock': m.get('stock'),
        }
        try:
            self.api.put_json(f"/api/merchant/menus/{m.get('id')}", body)
            self.snack('Ketersediaan menu diperbarui.', EMER_SOFT)
        except ApiError as ex:
            self.snack(str(ex), RED_SOFT)
        self.show_menus()

    def menu_form(self, menu_id=None):
        self.set_view(self.loading_view('Memuat data menu...'), tab_index=2)
        menu = {}
        if menu_id is not None:
            try:
                data = self.api.get_json('/api/merchant/menus') or []
                for m in data:
                    if str(m.get('id')) == str(menu_id):
                        menu = m
                        break
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)
        f_name = field('Nama menu', value=menu.get('name') or '')
        f_desc = field('Deskripsi', value=menu.get('description') or '', multiline=True, min_lines=2, max_lines=4)
        f_price = field('Harga (angka saja)', value=str(int(menu.get('price') or 0)) if menu.get('price') else '',
                        keyboard_type=ft.KeyboardType.NUMBER)
        f_cat = field('Kategori', value=menu.get('category') or '')
        f_img = field('URL foto', value=menu.get('image_url') or '')
        stock_val = menu.get('stock')
        f_stock = field('Stok (kosong = tidak dibatasi)',
                        value='' if stock_val is None else str(int(stock_val)),
                        keyboard_type=ft.KeyboardType.NUMBER)
        sw_avail = ft.Switch(label='Tersedia', value=bool(menu.get('is_available', True)),
                             active_color=EMER, label_style=ft.TextStyle(color=TXT, size=13))

        def save(e):
            name = (f_name.value or '').strip()
            if not name:
                self.snack('Nama menu wajib diisi.', RED_SOFT)
                return
            try:
                price = int(float((f_price.value or '0').replace('.', '').replace(',', '') or 0))
            except Exception:
                self.snack('Harga harus berupa angka.', RED_SOFT)
                return
            stock_raw = (f_stock.value or '').strip()
            try:
                stock = None if stock_raw == '' else int(float(stock_raw))
            except Exception:
                self.snack('Stok harus berupa angka atau dikosongkan.', RED_SOFT)
                return
            body = {
                'name': name,
                'description': (f_desc.value or '').strip(),
                'price': price,
                'is_available': bool(sw_avail.value),
                'category': (f_cat.value or '').strip(),
                'image_url': (f_img.value or '').strip(),
                'stock': stock,
            }
            try:
                if menu_id is None:
                    self.api.post_json('/api/merchant/menus', body)
                    self.snack('Menu baru ditambahkan.', EMER_SOFT)
                else:
                    self.api.put_json(f'/api/merchant/menus/{menu_id}', body)
                    self.snack('Menu diperbarui.', EMER_SOFT)
                self.show_menus()
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)

        def confirm_delete(e):
            self.close_dialog()
            try:
                self.api.delete(f'/api/merchant/menus/{menu_id}')
                self.snack('Menu dihapus.', EMER_SOFT)
                self.show_menus()
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)

        def ask_delete(e):
            self.open_dialog(ft.AlertDialog(
                modal=True, bgcolor=CARD,
                title=txt('Hapus menu ini?', size=16, weight=ft.FontWeight.W_600),
                content=txt('Menu akan dihapus permanen dari daftar jualan toko.', size=12, color=DIM),
                actions=[ft.TextButton(content=txt('Batal', size=13, color=DIM),
                                       on_click=self.safe(lambda ev: self.close_dialog())),
                         gold_button('Hapus', self.safe(confirm_delete))]))

        form_controls = [
            section('Data menu'),
            f_name, f_desc, f_price, f_cat, f_img, f_stock, sw_avail,
            gold_button('Simpan', self.safe(save), icon=ft.Icons.SAVE_ROUNDED, expand=True),
        ]
        if menu_id is not None:
            form_controls.append(gold_button('Hapus menu', self.safe(ask_delete),
                                             icon=ft.Icons.DELETE_OUTLINE_ROUNDED, outline=True, expand=True))
        body = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12,
                           controls=[card(ft.Column(form_controls, spacing=12))])
        self.set_view(ft.Column(expand=True, spacing=0, controls=[
            self.sub_header('Tambah Menu' if menu_id is None else 'Ubah Menu', self.show_menus),
            body,
        ]), tab_index=2)

    # ---------------- KEUANGAN ----------------
    def show_finance(self, e=None):
        self.set_view(self.loading_view('Memuat data keuangan...'), tab_index=3, fab=None)
        try:
            summary = self.api.get_json('/api/merchant/finance/summary') or {}
            ledger = self.api.get_json('/api/merchant/finance/ledger', limit=100) or []
            withdrawals = self.api.get_json('/api/merchant/withdrawals') or []
            banks = self.api.get_json('/api/merchant/bank-accounts') or []
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), self.show_finance), tab_index=3)
            return
        self.fin_summary = summary
        self.fin_banks = banks if isinstance(banks, list) else (banks.get('items') if isinstance(banks, dict) else []) or []

        honesty = txt(
            'Saldo bertambah HANYA setelah admin memverifikasi settlement per pesanan. '
            'Pencairan bersifat manual: pending → approved → paid (admin transfer manual, tidak ada payout otomatis).',
            size=11, color=DIM)

        ringkasan = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[
            card(ft.Column([
                section('Saldo tersedia'),
                txt(rp(summary.get('available_balance')), size=34, color=GOLD, weight=ft.FontWeight.BOLD),
                ft.Row([txt('Ditahan pengajuan: ' + rp(summary.get('pending_withdrawal_total')), size=12, color=DIM)],
                       wrap=True),
                ft.Row([txt('Total ledger: ' + rp(summary.get('ledger_total')), size=12, color=DIM)], wrap=True),
            ], spacing=8)),
            card(ft.Column([
                section('Status settlement'),
                self.kv_row('Settlement menunggu verifikasi', str(int(summary.get('settlements_pending') or 0)), GOLD),
                self.kv_row('Settlement disetujui', str(int(summary.get('settlements_approved') or 0)), EMER),
                ft.Divider(color=BORDER, height=16),
                honesty,
                txt(summary.get('note') or '', size=11, color=DIM),
            ], spacing=8)),
            card(ft.Column([
                section('Laporan'),
                txt('Unduh laporan transaksi dalam format CSV sesuai rentang tanggal.', size=12, color=DIM),
                gold_button('Unduh laporan CSV', self.safe(lambda ev: self.csv_dialog()),
                            icon=ft.Icons.DOWNLOAD_ROUNDED, expand=True),
            ], spacing=10)),
        ])

        ledger_rows = []
        for en in ledger:
            amt = float(en.get('amount') or 0)
            kind = LEDGER_LABEL.get(str(en.get('kind') or '').lower(), str(en.get('kind') or '-').replace('_', ' ').title())
            ledger_rows.append(ft.Row([
                circle_icon(ft.Icons.ARROW_DOWNWARD_ROUNDED if amt >= 0 else ft.Icons.ARROW_UPWARD_ROUNDED,
                            EMER if amt >= 0 else RED, 36),
                ft.Column([
                    txt(kind, size=13, weight=ft.FontWeight.W_600),
                    txt(f"{fmt_dt(en.get('created_at'))} · {en.get('note') or en.get('ref') or '-'}", size=11, color=DIM),
                ], spacing=1, expand=True),
                txt(('+' if amt >= 0 else '') + rp(amt), size=13, color=EMER if amt >= 0 else RED,
                    weight=ft.FontWeight.W_600),
            ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=10))
        if not ledger_rows:
            ledger_rows = [self.empty_view('Belum ada entri ledger.', ft.Icons.RECEIPT_ROUNDED)]
        riwayat = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=ledger_rows)

        wd_rows = [self.withdrawal_tile(w) for w in withdrawals] or \
            [self.empty_view('Belum ada pengajuan pencairan.', ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED)]
        pencairan = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[
            card(ft.Column([
                section('Ajukan pencairan'),
                txt('Dana cair setelah admin memverifikasi dan mentransfer manual ke rekening Anda.',
                    size=12, color=DIM),
                gold_button('Ajukan pencairan', self.safe(lambda ev: self.withdraw_dialog()),
                            icon=ft.Icons.ACCOUNT_BALANCE_ROUNDED, expand=True),
            ], spacing=10)),
        ] + wd_rows)

        bank_rows = [self.bank_tile(b) for b in self.fin_banks] or \
            [self.empty_view('Belum ada rekening terdaftar.', ft.Icons.ACCOUNT_BALANCE_ROUNDED)]
        rekening = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[
            card(ft.Column([
                section('Rekening bank'),
                txt('Rekening dipakai sebagai tujuan transfer pencairan.', size=12, color=DIM),
                gold_button('Tambah rekening', self.safe(lambda ev: self.bank_dialog()),
                            icon=ft.Icons.ADD_ROUNDED, expand=True),
            ], spacing=10)),
        ] + bank_rows)

        tabs = ft.Tabs(
            selected_index=self.fin_tab,
            animation_duration=200,
            divider_color=BORDER,
            indicator_color=GOLD,
            label_color=GOLD,
            unselected_label_color=DIM,
            on_change=self.safe(self.on_fin_tab),
            expand=True,
            tabs=[
                ft.Tab(text='Ringkasan', content=ringkasan),
                ft.Tab(text='Riwayat', content=riwayat),
                ft.Tab(text='Pencairan', content=pencairan),
                ft.Tab(text='Rekening', content=rekening),
            ])
        self.set_view(ft.Column(expand=True, spacing=0, controls=[
            gradient_header(ft.Column([
                txt('Keuangan', size=20, weight=ft.FontWeight.BOLD),
                txt('Saldo tersedia', size=11, color=DIM),
                txt(rp(summary.get('available_balance')), size=26, color=GOLD, weight=ft.FontWeight.BOLD),
                honesty,
            ], spacing=4)),
            tabs,
        ]), tab_index=3)

    def on_fin_tab(self, e):
        try:
            self.fin_tab = int(e.control.selected_index)
        except Exception:
            self.fin_tab = 0

    def kv_row(self, label, value, color=TXT):
        return ft.Row([ft.Container(expand=True, content=txt(label, size=12, color=DIM)),
                       txt(value, size=13, color=color, weight=ft.FontWeight.W_600)],
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def withdrawal_tile(self, w):
        st = str(w.get('status') or '').lower()
        tone = {'pending': GOLD, 'approved': EMER, 'paid': EMER, 'rejected': RED}.get(st, DIM)
        bg = {'pending': GOLD_SOFT, 'approved': EMER_SOFT, 'paid': EMER_SOFT, 'rejected': RED_SOFT}.get(st, BLUE_SOFT)
        rows = [
            ft.Row([ft.Container(content=txt(rp(w.get('amount')), size=16, color=GOLD, weight=ft.FontWeight.BOLD), expand=True),
                    ft.Container(content=txt(WITHDRAW_LABEL.get(st, st.title() or '-'), size=10, color=tone,
                                             weight=ft.FontWeight.W_600),
                                 bgcolor=bg, border=ft.border.all(1, tone),
                                 border_radius=ft.border_radius.all(9),
                                 padding=ft.padding.symmetric(horizontal=10, vertical=4))]),
            txt(f"{w.get('bank_name') or '-'} · {w.get('account_no') or '-'} · {w.get('account_name') or '-'}",
                size=12, color=DIM),
            txt(f"Diajukan {fmt_dt(w.get('created_at'))}", size=11, color=DIM),
        ]
        if w.get('reviewed_at'):
            rows.append(txt(f"Ditinjau {fmt_dt(w.get('reviewed_at'))} oleh {w.get('reviewed_by') or 'admin'}",
                            size=11, color=DIM))
        if w.get('note'):
            rows.append(txt('Catatan admin: ' + str(w.get('note')), size=11, color=DIM))
        if w.get('client_ref'):
            rows.append(txt('Ref: ' + str(w.get('client_ref')), size=10, color=DIM))
        return card(ft.Column(rows, spacing=6))

    def bank_tile(self, b):
        def do_delete(e):
            try:
                self.api.delete(f"/api/merchant/bank-accounts/{b.get('id')}")
                self.snack('Rekening dihapus.', EMER_SOFT)
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)
            self.show_finance()

        def ask(e):
            self.open_dialog(ft.AlertDialog(
                modal=True, bgcolor=CARD,
                title=txt('Hapus rekening?', size=16, weight=ft.FontWeight.W_600),
                content=txt(f"{b.get('bank_name') or '-'} {b.get('account_no') or ''}", size=12, color=DIM),
                actions=[ft.TextButton(content=txt('Batal', size=13, color=DIM),
                                       on_click=self.safe(lambda ev: self.close_dialog())),
                         gold_button('Hapus', self.safe(do_delete))]))

        return card(ft.Row([
            circle_icon(ft.Icons.ACCOUNT_BALANCE_ROUNDED, GOLD, 40),
            ft.Column([
                txt(b.get('bank_name') or '-', size=13, weight=ft.FontWeight.W_600),
                txt(f"{b.get('account_no') or '-'} · {b.get('account_name') or '-'}", size=11, color=DIM),
                txt('Utama' if b.get('is_primary') else 'Cadangan', size=10,
                    color=EMER if b.get('is_primary') else DIM),
            ], spacing=2, expand=True),
            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=RED,
                          tooltip='Hapus rekening', on_click=self.safe(ask)),
        ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=10), padding=14)

    def bank_dialog(self):
        f_bank = field('Nama bank (mis. BCA)')
        f_no = field('Nomor rekening', keyboard_type=ft.KeyboardType.NUMBER)
        f_name = field('Nama pemilik rekening')
        sw_primary = ft.Switch(label='Jadikan rekening utama', value=not bool(self.fin_banks),
                               active_color=EMER, label_style=ft.TextStyle(color=TXT, size=13))

        def save(e):
            bank = (f_bank.value or '').strip()
            no = (f_no.value or '').strip()
            name = (f_name.value or '').strip()
            if not bank or not no or not name:
                self.snack('Nama bank, nomor rekening, dan nama pemilik wajib diisi.', RED_SOFT)
                return
            try:
                self.api.post_json('/api/merchant/bank-accounts',
                                   {'bank_name': bank, 'account_no': no, 'account_name': name,
                                    'is_primary': bool(sw_primary.value)})
                self.close_dialog()
                self.snack('Rekening ditambahkan.', EMER_SOFT)
                self.show_finance()
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)

        self.open_dialog(ft.AlertDialog(
            modal=True, bgcolor=CARD,
            title=txt('Tambah rekening', size=16, weight=ft.FontWeight.W_600),
            content=ft.Column([f_bank, f_no, f_name, sw_primary], spacing=12, tight=True, width=320),
            actions=[ft.TextButton(content=txt('Batal', size=13, color=DIM),
                                   on_click=self.safe(lambda ev: self.close_dialog())),
                     gold_button('Simpan', self.safe(save))]))

    def withdraw_dialog(self):
        f_amount = field('Jumlah (angka saja)', keyboard_type=ft.KeyboardType.NUMBER)
        options = []
        for b in self.fin_banks:
            label = f"{b.get('bank_name') or '-'} · {b.get('account_no') or '-'} ({b.get('account_name') or '-'})"
            options.append(ft.dropdown.Option(key=str(b.get('id')), text=label))
        f_bank_dd = ft.Dropdown(options=options, label='Rekening tujuan', bgcolor=CARD2, border_color=BORDER,
                                focused_border_color=GOLD, color=TXT, border_radius=14, text_size=13,
                                value=str(options[0].key) if options else None)
        f_bank = field('Nama bank (isi bila belum ada rekening tersimpan)')
        f_no = field('Nomor rekening')
        f_name = field('Nama pemilik')
        info = txt('Pengajuan berstatus pending sampai admin memverifikasi. Status akhir: paid setelah admin '
                   'mentransfer manual.', size=11, color=DIM)

        def save(e):
            raw = (f_amount.value or '').replace('.', '').replace(',', '').strip()
            try:
                amount = int(float(raw))
            except Exception:
                self.snack('Jumlah pencairan harus berupa angka.', RED_SOFT)
                return
            if amount <= 0:
                self.snack('Jumlah pencairan harus lebih dari 0.', RED_SOFT)
                return
            body = {'amount': amount, 'client_ref': uuid.uuid4().hex}
            if options and f_bank_dd.value:
                body['bank_account_id'] = int(f_bank_dd.value)
            else:
                bank = (f_bank.value or '').strip()
                no = (f_no.value or '').strip()
                name = (f_name.value or '').strip()
                if not (bank and no and name):
                    self.snack('Pilih rekening tersimpan atau isi data rekening manual.', RED_SOFT)
                    return
                body.update({'bank_name': bank, 'account_no': no, 'account_name': name})
            try:
                self.api.post_json('/api/merchant/withdrawals', body)
                self.close_dialog()
                self.snack('Pengajuan pencairan terkirim. Menunggu review admin.', EMER_SOFT)
                self.show_finance()
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)

        manual = [] if options else [f_bank, f_no, f_name]
        self.open_dialog(ft.AlertDialog(
            modal=True, bgcolor=CARD,
            title=txt('Ajukan pencairan', size=16, weight=ft.FontWeight.W_600),
            content=ft.Column([f_amount, f_bank_dd] + manual + [info], spacing=12, tight=True, width=320),
            actions=[ft.TextButton(content=txt('Batal', size=13, color=DIM),
                                   on_click=self.safe(lambda ev: self.close_dialog())),
                     gold_button('Kirim pengajuan', self.safe(save))]))

    def report_dir(self):
        for name in ('get_application_documents_directory', 'get_downloads_directory'):
            fn = getattr(self.page, name, None)
            if callable(fn):
                try:
                    p = fn()
                    if p:
                        return p
                except Exception:
                    pass
        try:
            return tempfile.gettempdir()
        except Exception:
            return os.getcwd()

    def csv_dialog(self):
        today = date.today()
        first = today.replace(day=1)
        f_from = field('Dari tanggal (YYYY-MM-DD)', value=first.isoformat())
        f_to = field('Sampai tanggal (YYYY-MM-DD)', value=today.isoformat())

        def download(e):
            d1 = (f_from.value or '').strip()
            d2 = (f_to.value or '').strip()
            try:
                r = self.api.request('GET', '/api/merchant/finance/report.csv',
                                     params={'date_from': d1, 'date_to': d2})
                text = r.text or ''
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)
                return
            path = os.path.join(str(self.report_dir()), f'laporan-degofood-{d1}_{d2}.csv')
            try:
                with open(path, 'w', encoding='utf-8', newline='') as fh:
                    fh.write(text)
            except Exception as ex:
                traceback.print_exc()
                self.snack(f'Gagal menyimpan file: {ex}', RED_SOFT)
                return
            self.close_dialog()
            self.snack('Laporan disimpan: ' + path, EMER_SOFT)
            self.open_dialog(ft.AlertDialog(
                modal=True, bgcolor=CARD,
                title=txt('Laporan CSV siap', size=16, weight=ft.FontWeight.W_600),
                content=ft.Column([
                    txt('File tersimpan di:', size=11, color=DIM),
                    txt(path, size=12),
                    txt(f'{len(text)} karakter', size=11, color=DIM),
                ], spacing=8, tight=True, width=320),
                actions=[
                    ft.TextButton(content=txt('Salin isi CSV', size=13, color=GOLD),
                                  on_click=self.safe(lambda ev: self.copy_csv(text))),
                    gold_button('Tutup', self.safe(lambda ev: self.close_dialog())),
                ]))

        self.open_dialog(ft.AlertDialog(
            modal=True, bgcolor=CARD,
            title=txt('Unduh laporan CSV', size=16, weight=ft.FontWeight.W_600),
            content=ft.Column([f_from, f_to], spacing=12, tight=True, width=320),
            actions=[ft.TextButton(content=txt('Batal', size=13, color=DIM),
                                   on_click=self.safe(lambda ev: self.close_dialog())),
                     gold_button('Unduh', self.safe(download))]))

    def copy_csv(self, text):
        try:
            self.page.set_clipboard(text)
            self.snack('Isi CSV disalin ke clipboard.', EMER_SOFT)
        except Exception as ex:
            self.snack(f'Gagal menyalin: {ex}', RED_SOFT)

    # ---------------- LAINNYA ----------------
    def show_more(self, e=None):
        self.view_name = 'more'
        acc = self.account or {}
        rest = self.restaurant or {}
        rows = [
            ('Profil Toko', ft.Icons.STORE_MALL_DIRECTORY_ROUNDED, 'show_profile_page'),
            ('Promo', ft.Icons.LOCAL_OFFER_ROUNDED, 'show_promo_page'),
            ('Notifikasi', ft.Icons.NOTIFICATIONS_ROUNDED, 'show_notifications_page'),
            ('Server', ft.Icons.DNS_ROUNDED, 'show_server_page'),
        ]
        tiles = []
        for label, icon, handler in rows:
            tiles.append(ft.Container(
                bgcolor=CARD2, border_radius=16, border=ft.border.all(1, BORDER), padding=14, ink=True,
                on_click=self.safe(lambda e, h=handler: getattr(self, h)()),
                content=ft.Row([
                    circle_icon(icon, GOLD, 40),
                    ft.Container(expand=True, content=txt(label, size=14, weight=ft.FontWeight.W_600)),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=DIM, size=20),
                ], vertical_alignment=ft.VerticalAlignment.CENTER, spacing=12)))

        self.set_view(ft.Container(expand=True, content=ft.ListView(
            expand=True, spacing=12, padding=ft.padding.all(16), controls=[
                gradient_header(ft.Column([
                    section('Akun'),
                    txt(acc.get('name') or rest.get('name') or 'Merchant', size=20, weight=ft.FontWeight.BOLD),
                    txt(acc.get('email') or acc.get('phone') or '-', size=12, color=DIM),
                ], spacing=4)),
            ] + tiles + [
                ft.Container(height=6),
                gold_button('Keluar dari akun', self.safe(self.ask_logout),
                            icon=ft.Icons.LOGOUT_ROUNDED, outline=True, expand=True),
                txt('Versi aplikasi merchant 1.0.0 · server: ' + self.api.base, size=10, color=DIM),
                ft.Container(height=8),
            ])), tab_index=4, fab=None)

    def ask_logout(self, e):
        self.open_dialog(ft.AlertDialog(
            modal=True, bgcolor=CARD,
            title=txt('Keluar dari akun?', size=16, weight=ft.FontWeight.W_600),
            content=txt('Anda perlu memasukkan kembali nomor HP/email dan password.', size=12, color=DIM),
            actions=[ft.TextButton(content=txt('Batal', size=13, color=DIM),
                                   on_click=self.safe(lambda ev: self.close_dialog())),
                     gold_button('Keluar', self.safe(self.do_logout))]))

    def do_logout(self, e):
        self.close_dialog()
        self.logout_click(e)

    # ---------------- PROFIL ----------------
    def show_profile_page(self, e=None):
        self.view_name = 'profile'
        self.set_view(self.loading_view('Memuat profil toko...'), tab_index=4)
        try:
            prof = self.api.get_json('/api/merchant/profile') or {}
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), self.show_profile_page), tab_index=4)
            return
        self.profile = prof
        f_desc = field('Deskripsi toko', value=prof.get('description') or '', multiline=True,
                       min_lines=2, max_lines=4)
        f_open = field('Jam buka (mis. 08:00)', value=str(prof.get('open_time') or ''))
        f_close = field('Jam tutup (mis. 21:00)', value=str(prof.get('close_time') or ''))
        f_min = field('Minimum order (angka)', value=str(int(prof.get('min_order') or 0)),
                      keyboard_type=ft.KeyboardType.NUMBER)
        sw_accept = ft.Switch(label='Terima pesanan baru', value=bool(prof.get('is_accepting_orders', True)),
                              active_color=EMER, label_style=ft.TextStyle(color=TXT, size=13))
        sw_open = ft.Switch(label='Toko buka', value=bool(prof.get('is_open')), active_color=EMER,
                            label_style=ft.TextStyle(color=TXT, size=13))

        def save(e):
            try:
                min_order = int(float((f_min.value or '0').replace('.', '').replace(',', '') or 0))
            except Exception:
                self.snack('Minimum order harus berupa angka.', RED_SOFT)
                return
            body = {
                'description': (f_desc.value or '').strip(),
                'open_time': (f_open.value or '').strip(),
                'close_time': (f_close.value or '').strip(),
                'min_order': min_order,
                'is_accepting_orders': bool(sw_accept.value),
                'is_open': bool(sw_open.value),
            }
            try:
                self.api.put_json('/api/merchant/profile', body)
                self.snack('Profil toko disimpan.', EMER_SOFT)
                self.show_profile_page()
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)

        body_view = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[
            card(ft.Column([
                section('Identitas toko'),
                txt(prof.get('name') or '-', size=16, weight=ft.FontWeight.W_600),
                txt(prof.get('address') or 'Alamat belum diisi.', size=12, color=DIM),
                txt('Telepon: ' + str(prof.get('phone') or '-'), size=12, color=DIM),
                txt('Restaurant ID: ' + str(prof.get('restaurant_id') or '-'), size=11, color=DIM),
            ], spacing=6)),
            card(ft.Column([
                section('Pengaturan jualan'),
                f_desc, f_open, f_close, f_min, sw_accept, sw_open,
                gold_button('Simpan profil', self.safe(save), icon=ft.Icons.SAVE_ROUNDED, expand=True),
            ], spacing=12)),
            ft.Container(height=8),
        ])
        self.set_view(ft.Column(expand=True, spacing=0, controls=[
            self.sub_header('Profil Toko', self.show_more), body_view]), tab_index=4)

    # ---------------- PROMO ----------------
    def show_promo_page(self, e=None):
        self.view_name = 'promo'
        self.set_view(self.loading_view('Memuat promo...'), tab_index=4)
        try:
            promos = self.api.get_json('/api/merchant/promos') or []
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), self.show_promo_page), tab_index=4)
            return
        note = txt('Catatan jujur: promo belum diterapkan di checkout pelanggan '
                   '(applied_at_checkout = false). Promo hanya tercatat di sisi merchant.', size=11, color=GOLD)
        tiles = []
        for p in promos:
            dtype = 'Persen' if str(p.get('discount_type')) == 'percent' else 'Potongan'
            val = p.get('discount_value')
            val_txt = (f"{val}%" if str(p.get('discount_type')) == 'percent' else rp(val))
            tiles.append(ft.Container(
                bgcolor=CARD2, border_radius=18, border=ft.border.all(1, BORDER), padding=14, ink=True,
                on_click=self.safe(lambda e, pid=p.get('id'): self.promo_form(pid)),
                content=ft.Column([
                    ft.Row([ft.Container(content=txt(p.get('code') or '-', size=14, color=GOLD, weight=ft.FontWeight.BOLD), expand=True),
                            ft.Container(content=txt('Aktif' if p.get('is_active') else 'Nonaktif', size=10,
                                                     color=EMER if p.get('is_active') else DIM,
                                                     weight=ft.FontWeight.W_600),
                                         bgcolor=EMER_SOFT if p.get('is_active') else BLUE_SOFT,
                                         border=ft.border.all(1, EMER if p.get('is_active') else BORDER),
                                         border_radius=ft.border_radius.all(8),
                                         padding=ft.padding.symmetric(horizontal=8, vertical=3))]),
                    txt(p.get('title') or '-', size=13, weight=ft.FontWeight.W_600),
                    txt(p.get('description') or '', size=11, color=DIM),
                    txt(f'{dtype} {val_txt} · min order {rp(p.get("min_order"))}', size=11, color=DIM),
                    txt(f"Diterapkan di checkout: {bool(p.get('applied_at_checkout'))}", size=11, color=DIM),
                    txt(str(p.get('note') or ''), size=11, color=DIM),
                    txt(f"Berlaku {fmt_dt(p.get('starts_at'))} s/d {fmt_dt(p.get('ends_at'))}", size=10, color=DIM),
                ], spacing=5)))
        if not tiles:
            tiles = [self.empty_view('Belum ada promo.', ft.Icons.LOCAL_OFFER_ROUNDED)]
        self.set_view(ft.Column(expand=True, spacing=0, controls=[
            self.sub_header('Promo', self.show_more),
            ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[
                card(ft.Column([
                    section('Promo toko'),
                    note,
                    gold_button('Tambah promo', self.safe(lambda ev: self.promo_form(None)),
                                icon=ft.Icons.ADD_ROUNDED, expand=True),
                ], spacing=10)),
            ] + tiles),
        ]), tab_index=4)

    def promo_form(self, promo_id=None):
        promo = {}
        if promo_id is not None:
            try:
                data = self.api.get_json('/api/merchant/promos') or []
                for p in data:
                    if str(p.get('id')) == str(promo_id):
                        promo = p
                        break
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)
        f_code = field('Kode promo (mis. HEMAT10)', value=promo.get('code') or '')
        f_title = field('Judul', value=promo.get('title') or '')
        f_desc = field('Deskripsi', value=promo.get('description') or '', multiline=True, min_lines=2, max_lines=3)
        f_type = ft.Dropdown(options=[ft.dropdown.Option(key='percent', text='Persen (%)'),
                                      ft.dropdown.Option(key='amount', text='Potongan nominal (Rp)')],
                             value=str(promo.get('discount_type') or 'percent'), label='Jenis diskon',
                             bgcolor=CARD2, border_color=BORDER, focused_border_color=GOLD, color=TXT,
                             border_radius=14, text_size=13)
        f_val = field('Nilai diskon', value=str(promo.get('discount_value') or ''),
                      keyboard_type=ft.KeyboardType.NUMBER)
        f_min = field('Minimum order', value=str(int(promo.get('min_order') or 0)),
                      keyboard_type=ft.KeyboardType.NUMBER)
        f_start = field('Mulai (YYYY-MM-DDTHH:MM:SS)', value=str(promo.get('starts_at') or ''))
        f_end = field('Berakhir (YYYY-MM-DDTHH:MM:SS)', value=str(promo.get('ends_at') or ''))
        sw_active = ft.Switch(label='Aktif', value=bool(promo.get('is_active', True)), active_color=EMER,
                              label_style=ft.TextStyle(color=TXT, size=13))
        warn = txt('Promo belum diterapkan di checkout pelanggan (applied_at_checkout = false).', size=11, color=GOLD)

        def save(e):
            code = (f_code.value or '').strip()
            title = (f_title.value or '').strip()
            if not code or not title:
                self.snack('Kode dan judul promo wajib diisi.', RED_SOFT)
                return
            try:
                val = float((f_val.value or '0').replace('.', '').replace(',', '') or 0)
                min_order = int(float((f_min.value or '0').replace('.', '').replace(',', '') or 0))
            except Exception:
                self.snack('Nilai diskon dan minimum order harus berupa angka.', RED_SOFT)
                return
            body = {
                'code': code,
                'title': title,
                'description': (f_desc.value or '').strip(),
                'discount_type': f_type.value or 'percent',
                'discount_value': val,
                'min_order': min_order,
                'is_active': bool(sw_active.value),
                'starts_at': (f_start.value or '').strip() or None,
                'ends_at': (f_end.value or '').strip() or None,
            }
            try:
                if promo_id is None:
                    self.api.post_json('/api/merchant/promos', body)
                    self.snack('Promo ditambahkan.', EMER_SOFT)
                else:
                    self.api.put_json(f'/api/merchant/promos/{promo_id}', body)
                    self.snack('Promo diperbarui.', EMER_SOFT)
                self.show_promo_page()
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)

        def do_delete(e):
            self.close_dialog()
            try:
                self.api.delete(f'/api/merchant/promos/{promo_id}')
                self.snack('Promo dihapus.', EMER_SOFT)
                self.show_promo_page()
            except ApiError as ex:
                self.snack(str(ex), RED_SOFT)

        controls = [section('Data promo'), f_code, f_title, f_desc, f_type, f_val, f_min, f_start, f_end,
                    sw_active, warn,
                    gold_button('Simpan', self.safe(save), icon=ft.Icons.SAVE_ROUNDED, expand=True)]
        if promo_id is not None:
            controls.append(gold_button('Hapus promo', self.safe(lambda ev: self.open_dialog(ft.AlertDialog(
                modal=True, bgcolor=CARD,
                title=txt('Hapus promo ini?', size=16, weight=ft.FontWeight.W_600),
                content=txt(str(promo.get('code') or ''), size=12, color=DIM),
                actions=[ft.TextButton(content=txt('Batal', size=13, color=DIM),
                                       on_click=self.safe(lambda ev2: self.close_dialog())),
                         gold_button('Hapus', self.safe(do_delete))]))),
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED, outline=True, expand=True))
        self.set_view(ft.Column(expand=True, spacing=0, controls=[
            self.sub_header('Tambah Promo' if promo_id is None else 'Ubah Promo', self.show_promo_page),
            ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12,
                        controls=[card(ft.Column(controls, spacing=12))]),
        ]), tab_index=4)

    # ---------------- NOTIFIKASI ----------------
    def show_notifications_page(self, e=None):
        self.view_name = 'notifications'
        self.notif_col = ft.Column(spacing=12)
        self.set_view(self.loading_view('Memuat notifikasi...'), tab_index=4)
        try:
            self.fetch_notifications(silent=False)
        except ApiError as ex:
            self.set_view(self.error_view(str(ex), self.show_notifications_page), tab_index=4)
            return
        self.render_notif_list()
        self.start_polling()

    def fetch_notifications(self, silent=True):
        data = self.api.get_json('/api/merchant/notifications',
                                 since_order_id=self.cursors.get('order') or 0,
                                 since_event_id=self.cursors.get('event') or 0) or {}
        items = data.get('items') or []
        self.notif_note = data.get('note') or ''
        if data.get('new_order_cursor') is not None:
            self.cursors['order'] = int(data.get('new_order_cursor') or 0)
        if data.get('event_cursor') is not None:
            self.cursors['event'] = int(data.get('event_cursor') or 0)
        self._save_cursors()
        known = {str(i.get('id')) for i in self.notif_items}
        for it in items:
            if str(it.get('id')) not in known:
                self.notif_items.insert(0, it)
        del self.notif_items[200:]
        if items and silent and self.view_name == 'notifications':
            self.render_notif_list()

    def render_notif_list(self):
        tiles = []
        for n in self.notif_items:
            tiles.append(card(ft.Column([
                ft.Row([ft.Container(content=txt(n.get('title') or 'Notifikasi', size=14, weight=ft.FontWeight.W_600), expand=True),
                        txt(fmt_dt(n.get('created_at')), size=10, color=DIM)]),
                txt(n.get('body') or '', size=12, color=DIM),
                txt('Jenis: ' + str(n.get('kind') or '-') + ' · pesanan #' + str(n.get('order_id') or '-'),
                    size=10, color=DIM),
            ], spacing=4)))
        if not tiles:
            tiles = [self.empty_view('Belum ada notifikasi baru.', ft.Icons.NOTIFICATIONS_NONE_ROUNDED)]
        controls = [
            card(ft.Column([
                section('Notifikasi pesanan'),
                txt('Notifikasi hanya muncul saat aplikasi dibuka - belum push background. '
                    'Aplikasi memeriksa pesanan baru setiap 20 detik (foreground polling).', size=11, color=GOLD),
                txt('Mode server: ' + str(self.notif_note or 'foreground_polling'), size=11, color=DIM),
                txt(f"Kursor: order={self.cursors.get('order')}, event={self.cursors.get('event')}", size=10, color=DIM),
            ], spacing=6)),
        ] + tiles
        self.notif_col.controls = controls
        view = ft.Column(expand=True, spacing=0, controls=[
            self.sub_header('Notifikasi', self.show_more),
            ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[self.notif_col]),
        ])
        self.set_view(view, tab_index=4)

    def start_polling(self):
        if self.polling:
            return
        self.polling = True
        try:
            self.page.run_task(self._poll_loop)
        except Exception:
            traceback.print_exc()

            def loop():
                while self.polling:
                    time.sleep(20)
                    if not self.polling:
                        break
                    try:
                        self.fetch_notifications(silent=True)
                    except Exception:
                        traceback.print_exc()
            threading.Thread(target=loop, daemon=True).start()

    async def _poll_loop(self):
        while self.polling:
            await asyncio.sleep(20)
            if not self.polling:
                break
            try:
                self.fetch_notifications(silent=True)
            except ApiError as ex:
                print('polling error:', ex)
            except Exception:
                traceback.print_exc()

    def stop_polling(self):
        self.polling = False

    # ---------------- SERVER ----------------
    def show_server_page(self, e=None, back_to_login=False):
        self.view_name = 'server'
        self.server_field = field('Alamat server', value=self.api.base)
        self.server_result = txt('', size=12, color=DIM)
        self.server_result.visible = False

        def save(e):
            url = (self.server_field.value or '').strip().rstrip('/')
            if not url:
                self.snack('Alamat server tidak boleh kosong.', RED_SOFT)
                return
            if not (url.startswith('https://') or url.startswith('http://localhost') or url.startswith('http://127.0.0.1')):
                self.snack('Alamat harus diawali https:// (http hanya untuk localhost/127.0.0.1).', RED_SOFT)
                return
            self.api.set_base(url)
            try:
                self.page.client_storage.set(BASE_KEY, url)
            except Exception:
                traceback.print_exc()
            self.snack('Alamat server disimpan: ' + url, EMER_SOFT)

        def test(e):
            url = (self.server_field.value or '').strip().rstrip('/') or self.api.base
            self.server_result.value = 'Menguji koneksi ke ' + url + ' ...'
            self.server_result.color = DIM
            self.server_result.visible = True
            self.page.update()
            old = self.api.base
            self.api.set_base(url)
            try:
                r = self.api.request('GET', '/api/health')
                body = (r.text or '').strip()[:200]
                self.server_result.value = f'OK ({r.status_code}) dari {url}\n{body}'
                self.server_result.color = EMER
            except ApiError as ex:
                self.server_result.value = f'Gagal: {ex}'
                self.server_result.color = RED
            finally:
                self.api.set_base(old)
            self.page.update()

        body_view = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=12, controls=[
            card(ft.Column([
                section('Alamat server API'),
                txt('Bawaan: ' + API_BASE_URL, size=11, color=DIM),
                txt('Demi keamanan, hanya alamat https (atau http untuk localhost/127.0.0.1) yang dipakai. '
                    'Nilai lain akan diabaikan saat aplikasi dibuka.', size=11, color=DIM),
                self.server_field,
                ft.Row([
                    gold_button('Uji koneksi', self.safe(test), icon=ft.Icons.WIFI_TETHERING_ROUNDED, expand=True),
                    gold_button('Simpan', self.safe(save), icon=ft.Icons.SAVE_ROUNDED, outline=True, expand=True),
                ], spacing=10),
                self.server_result,
            ], spacing=12)),
        ])
        back = self.show_login if back_to_login else self.show_more
        self.set_view(ft.Column(expand=True, spacing=0, controls=[
            self.sub_header('Server', back), body_view]), tab_index=4, show_nav=not back_to_login)


def main(page: ft.Page):
    page.title = 'DEGOFOOD Merchant'
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0
    try:
        page.theme = ft.Theme(color_scheme_seed=GOLD)
    except Exception:
        pass
    app = MerchantApp(page)
    try:
        app.start()
    except Exception as ex:
        traceback.print_exc()
        page.add(ft.Container(expand=True, alignment=ft.alignment.center,
                              content=ft.Column([
                                  ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=RED, size=40),
                                  ft.Text('Gagal memulai aplikasi: ' + str(ex), color=RED),
                              ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)))
    try:
        page.on_disconnect = lambda e: app.stop_polling()
    except Exception:
        pass


if __name__ == '__main__':
    _port = int(os.environ.get('DEGOFOOD_PORT', '0') or 0)
    if _port:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=_port)
    else:
        ft.app(target=main)

