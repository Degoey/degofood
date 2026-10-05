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
API_BASE_URL = 'http://192.168.1.6:8000'

PRIMARY = ft.Colors.ORANGE_600
ACCENT = ft.Colors.ORANGE_700
BG_COLOR = '#F5F5F5'
DELIVERY_FEE = 5000
CUSTOMER_KEY = 'DEGOFOOD_customer'


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
