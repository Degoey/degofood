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
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_server.ps1
```

Atau manual:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API: http://127.0.0.1:8000
- Dokumentasi interaktif: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

**Port 8000 sudah dipakai program lain?** (mis. Docker Desktop yang mem-publish container ke 8000)
Jalankan backend di port lain tanpa perlu mengubah script:

```powershell
$env:DEGOFOOD_PORT = '8020'
.\run_server.ps1
```

> Tabel database dibuat otomatis saat pertama kali dijalankan (`Base.metadata.create_all`).

### 2. Admin Panel (port 8001)

```powershell
cd admin_panel
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_admin.ps1
```

Buka http://127.0.0.1:8001 dan login dengan `admin` / `admin123` (default).

Bila backend dijalankan di port lain, arahkan admin panel ke sana (dan opsional ubah port admin):

```powershell
$env:BACKEND_URL = 'http://127.0.0.1:8020'
$env:DEGOFOOD_ADMIN_PORT = '8001'
.\run_admin.ps1
```

### 3. Mobile App (desktop dev)

```powershell
cd mobile_app
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

> **Catatan penting:** selalu panggil `python.exe -m pip` dan `python.exe -m uvicorn`,
> jangan `pip.exe` / `uvicorn.exe`. Launcher `.exe` di dalam `venv\Scripts` menyimpan
> **path absolut** saat dibuat, sehingga rusak bila folder repo di-rename atau dipindah.
> Lihat bagian **Troubleshooting** di bawah.

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

Dengan backend (8000) dan admin panel (8001) sudah berjalan, jalankan dari **root repo**:

```powershell
.\backend\venv\Scripts\python.exe test_bag9.py
```

> Skrip ini butuh `httpx`, yang sudah termasuk dalam `backend/requirements.txt` —
> karena itu dipakai interpreter venv backend.

Bila backend / admin panel berjalan di port non-default, set variabel berikut
(default: `http://127.0.0.1:8000` dan `http://127.0.0.1:8001`):

```powershell
$env:BASE_BACKEND = 'http://127.0.0.1:8020'
$env:BASE_ADMIN   = 'http://127.0.0.1:8001'
.\backend\venv\Scripts\python.exe test_bag9.py
```

Skrip ini membuat restoran, menambah menu, mendaftarkan pelanggan, dan membuat pesanan lewat API untuk memverifikasi alur lengkap. Setel `ADMIN_USERNAME` / `ADMIN_PASSWORD` bila berbeda dari default.

Hasil yang diharapkan: semua langkah `status: 200`, diakhiri `Update status status: 200`.

---

## Troubleshooting

### `uvicorn.exe` / `pip.exe` rusak setelah folder di-rename

**Gejala:** `.\venv\Scripts\uvicorn.exe --version` gagal tanpa pesan jelas, atau service
tidak mau start padahal paket sudah ter-install.

**Penyebab:** saat `pip` meng-install paket, ia membuat launcher `.exe` di `venv\Scripts\`
yang menyimpan **path absolut** interpreter, contoh:

```
#!D:\FOODGO\admin_panel\venv\Scripts\python.exe
```

Bila folder repo di-rename (mis. `D:\FOODGO` → `D:\DEGOFOOD`), path itu menjadi tidak
valid dan launcher gagal — **walaupun isi `site-packages` masih utuh**.

**Solusi cepat (tanpa install ulang apa pun):** panggil modulnya lewat interpreter,
bukan lewat launcher `.exe`:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Cara ini sudah dipakai otomatis oleh `run_server.ps1` dan `run_admin.ps1`, sehingga
kedua script itu tetap berfungsi setelah folder dipindah.

**Solusi bersih (opsional):** buat ulang venv-nya.

```powershell
cd backend
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Menyembuhkan path lama di dalam venv** (`pyvenv.cfg`, `activate.bat`, `activate.ps1`)
agar `VIRTUAL_ENV` menunjuk ke lokasi baru:

```powershell
$venv = 'D:\DEGOFOOD\backend\venv'
foreach ($f in @("$venv\pyvenv.cfg", "$venv\Scripts\activate.bat", "$venv\Scripts\activate.ps1")) {
    if (Test-Path $f) {
        (Get-Content $f -Raw).Replace('D:\FOODGO', 'D:\DEGOFOOD') |
            Set-Content $f -NoNewline -Encoding ASCII
    }
}
```

### Port 8000 / 8001 sudah dipakai

Cek dulu siapa pemakainya:

```powershell
netstat -ano | Select-String ':8000\s'
Get-Process -Id <PID> | Select-Object Id, ProcessName, Path
```

Hentikan **hanya bila itu prosesmu sendiri**:

```powershell
taskkill /PID <PID> /F
```

**Jangan hentikan proses milik aplikasi lain.** Contoh nyata: **Docker Desktop**
(`com.docker.backend.exe`) yang mem-publish container ke port 8000 menempati port itu secara
permanen. Akibatnya request ke `http://127.0.0.1:8000` dilayani aplikasi container tersebut,
bukan DEGOFOOD — gejalanya `/api/health` membalas `{"detail":"Not Found"}`.

Solusinya: jalankan DEGOFOOD di port lain, lalu arahkan admin panel ke port itu.

```powershell
# terminal 1
cd backend
$env:DEGOFOOD_PORT = '8020'
.\run_server.ps1

# terminal 2
cd admin_panel
$env:BACKEND_URL = 'http://127.0.0.1:8020'
.\run_admin.ps1
```

> Catatan: `uvicorn --reload` menjalankan proses induk **dan** proses anak (worker). Bila port
> masih terpakai setelah `taskkill` pada PID di `netstat`, worker-nya masih hidup — temukan dengan
> `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` lalu hentikan PID tersebut.

### Health check backend

```powershell
curl http://127.0.0.1:8000/api/health
```

---

## Lisensi

Belum ditentukan.

