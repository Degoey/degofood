# DEGOFOOD 🍔

Aplikasi pemesanan makanan (*food delivery*) yang terdiri dari **REST API**, **Admin Panel web**, dan **aplikasi mobile**.

Dibangun dengan **Python + FastAPI** (backend & admin) dan **Flet** (aplikasi mobile Android/desktop).

---

## Fitur

**Untuk Pelanggan (mobile app)**
- Melihat daftar restoran yang sedang buka
- Melihat menu restoran dan menambahkan ke keranjang
- Keranjang belanja dengan biaya pengiriman otomatis (Rp 5.000)
- Membuat pesanan dengan alamat pengiriman dan catatan
- Melihat riwayat pesanan

**Untuk Restoran / Admin (web)**
- Dashboard ringkasan (total pesanan, restoran, pelanggan, pesanan tertunda)
- Kelola restoran: tambah, ubah, hapus, buka/tutup
- Kelola menu: tambah, hapus, aktif/nonaktif
- Kelola pesanan dan ubah statusnya
- Login sesi untuk melindungi halaman admin

**Notifikasi WhatsApp**
- Otomatis ke restoran saat ada pesanan baru masuk
- Otomatis ke pelanggan saat status pesanan berubah

> Saat ini notifikasi WhatsApp **disimulasikan** (dicetak ke log terminal). Untuk produksi, ganti isi fungsi `send_whatsapp_message` di `backend/app/services/whatsapp.py` dengan pemanggilan HTTP ke provider pilihanmu (WhatsApp Cloud API, Twilio, Fonnte, dll).

---

## Arsitektur

| Komponen | Teknologi | Port | Deskripsi |
|---|---|---|---|
| `backend/` | FastAPI + SQLAlchemy + SQLite | **8000** | REST API untuk mobile app & admin panel |
| `admin_panel/` | FastAPI + Jinja2 | **8001** | Web UI admin/restoran (server-side rendering) |
| `mobile_app/` | Flet (Python + Flutter) | — | Aplikasi mobile pelanggan, bisa di-build jadi APK |

Admin panel **tidak** mengakses database secara langsung — semua lewat REST API backend.

---

## Struktur Proyek

```
DEGOFOOD/
├── backend/                    # REST API (FastAPI)
│   ├── app/
│   │   ├── main.py             # entrypoint, CORS, registrasi router
│   │   ├── database.py         # engine & session SQLAlchemy
│   │   ├── models.py           # Restaurant, Menu, Customer, Order, OrderItem
│   │   ├── schemas.py          # skema Pydantic
│   │   ├── routers/            # restaurants, customers, orders, admin
│   │   └── services/
│   │       └── whatsapp.py     # notifikasi WhatsApp (simulasi)
│   ├── deploy/                 # script deploy ke VPS
│   │   ├── deploy.sh           # deploy utama (Ubuntu + systemd + Caddy)
│   │   ├── deploy_degofood_oneshot.ps1
│   │   ├── deploy_degofood_safe.sh
│   │   └── deploy_from_windows.ps1
│   ├── requirements.txt
│   ├── .env.example
│   └── run_server.ps1
├── admin_panel/                # Admin Panel web (FastAPI + Jinja2)
│   ├── main.py
│   ├── templates/
│   ├── requirements.txt
│   ├── .env.example
│   └── run_admin.ps1
├── mobile_app/                 # Aplikasi mobile (Flet)
│   ├── main.py
│   ├── parts/                  # modul UI
│   ├── build_apk.ps1
│   └── requirements.txt
├── DEPLOY.md                   # panduan deploy lengkap ke VPS
├── test_bag9.py                # skrip uji end-to-end (smoke test)
└── .gitattributes
```

---

## Prasyarat

- **Python 3.12+**
- **PowerShell** (Windows) — script `run_*.ps1` disediakan untuk kemudahan
- *(opsional, untuk build APK)* JDK 21, Android SDK, Flutter

---

## Menjalankan Secara Lokal

Jalankan **backend lebih dulu**, baru admin panel / mobile app.

### 1. Backend API (port 8000)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\run_server.ps1
```

Atau manual:

```powershell
cd backend
.\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API: http://127.0.0.1:8000
- Dokumentasi interaktif: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

> Tabel database dibuat otomatis saat pertama kali dijalankan (`Base.metadata.create_all`).

### 2. Admin Panel (port 8001)

```powershell
cd admin_panel
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\run_admin.ps1
```

Buka http://127.0.0.1:8001 dan login dengan `admin` / `admin123` (default).

### 3. Mobile App (desktop dev)

```powershell
cd mobile_app
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

---

## Konfigurasi `.env`

Salin `.env.example` menjadi `.env` di masing-masing folder. **Jangan pernah commit file `.env`.**

**`backend/.env`**

| Variabel | Default | Keterangan |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./food_delivery.db` | URL database SQLAlchemy |
| `ADMIN_API_KEY` | — | Kunci untuk endpoint `/api/admin/*` (Header `X-Admin-Key`) |
| `CORS_ORIGINS` | `*` | Origin yang diizinkan, pisahkan dengan koma |
| `SESSION_SECRET` | — | Secret sesi admin panel |

**`admin_panel/.env`**

| Variabel | Default | Keterangan |
|---|---|---|
| `BACKEND_URL` | `http://127.0.0.1:8000` | URL backend API |
| `ADMIN_USERNAME` | `admin` | Username login admin panel |
| `ADMIN_PASSWORD` | `admin123` | Password login admin panel |
| `ADMIN_API_KEY` | — | **Harus sama** dengan `ADMIN_API_KEY` di `backend/.env` |
| `SESSION_SECRET` | — | Secret session (minimal 32 karakter) |

> ⚠️ Jika `ADMIN_API_KEY` di backend diisi, endpoint admin akan menolak request tanpa header `X-Admin-Key` yang cocok. Pastikan nilai di kedua file **identik**.

---

## Endpoint API

### Publik

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/` | Info API |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/restaurants/` | Daftar restoran yang buka |
| `GET` | `/api/restaurants/{id}` | Detail restoran |
| `GET` | `/api/restaurants/{id}/menu` | Menu restoran yang tersedia |
| `POST` | `/api/restaurants/` | Tambah restoran |
| `POST` | `/api/restaurants/menu` | Tambah menu |
| `POST` | `/api/customers/` | Daftar pelanggan baru (nomor dinormalisasi ke `+62`) |
| `GET` | `/api/customers/` | Daftar semua pelanggan |
| `GET` | `/api/customers/phone/{phone}` | Cari pelanggan berdasarkan nomor |
| `PUT` | `/api/customers/{id}` | Ubah data pelanggan |
| `POST` | `/api/orders/` | Buat pesanan baru |
| `GET` | `/api/orders/` | Daftar semua pesanan |
| `GET` | `/api/orders/customer/{id}` | Pesanan milik seorang pelanggan |
| `PUT` | `/api/orders/{id}/status?status=...` | Ubah status pesanan |

### Admin (butuh header `X-Admin-Key`)

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/api/admin/summary` | Ringkasan statistik |
| `GET` | `/api/admin/restaurants` | Semua restoran |
| `POST` | `/api/admin/restaurants` | Tambah restoran |
| `PUT` | `/api/admin/restaurants/{id}` | Ubah restoran |
| `PUT` | `/api/admin/restaurants/{id}/toggle` | Buka/tutup restoran |
| `DELETE` | `/api/admin/restaurants/{id}` | Hapus restoran |
| `POST` | `/api/admin/restaurants/{id}/menus` | Tambah menu ke restoran |
| `PUT` | `/api/admin/menus/{id}/toggle` | Aktif/nonaktif menu |
| `DELETE` | `/api/admin/menus/{id}` | Hapus menu |
| `GET` | `/api/admin/orders` | Semua pesanan + nama pelanggan & restoran |
| `PUT` | `/api/admin/orders/{id}/status` | Ubah status pesanan |

**Status pesanan yang valid:**
`Menunggu Konfirmasi` → `Dikonfirmasi` → `Sedang Dimasak` → `Sedang Diantar` → `Selesai` (atau `Dibatalkan`)

---


## Deploy ke VPS

Panduan lengkap (Ubuntu + systemd + Caddy + HTTPS otomatis) ada di **[DEPLOY.md](DEPLOY.md)**.

Cara tercepat dari Windows:

```powershell
.\backend\deploy\deploy_from_windows.ps1 -Server "root@IP_VPS" -Port <PORT_SSH>
```

Tanpa domain, script otomatis memakai **sslip.io** sehingga HTTPS tetap aktif.

---

## Build APK Android

```powershell
cd mobile_app
.\build_apk.ps1 -ApiUrl "http://IP_SERVER:8000"
```

Sesuaikan `JAVA_HOME`, `ANDROID_SDK_ROOT`, dan lokasi Flutter di bagian atas `build_apk.ps1` bila berbeda.

---

## Uji End-to-End

Dengan backend (8000) dan admin panel (8001) sudah berjalan:

```powershell
python test_bag9.py
```

Skrip ini membuat restoran, menambah menu, mendaftarkan pelanggan, dan membuat pesanan lewat API untuk memverifikasi alur lengkap. Setel `ADMIN_USERNAME` / `ADMIN_PASSWORD` bila berbeda dari default.

---

## Lisensi

Belum ditentukan.

