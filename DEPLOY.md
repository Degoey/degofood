# Deploy DEGOFOOD ke VPS (Ubuntu + Domain + HTTPS)

Panduan ini menggunakan **VPS Ubuntu 22.04/24.04**, **Python venv**, dan **Caddy** sebagai reverse proxy + HTTPS otomatis. Alternatif Nginx juga disertakan.

---

## Cara Cepat (Otomatis)

Tersedia script yang mengotomatiskan seluruh langkah (install paket, salin kode, venv, `.env` + secret acak, seed, systemd, Caddy).

**Belum punya domain?** Script otomatis memakai **sslip.io** sehingga HTTPS tetap aktif tanpa beli domain.

### A. Tanpa domain (pakai IP VPS + sslip.io)

Dari Windows (PowerShell, di root repo):
```powershell
# <PORT_SSH> = port SSH VPS (default 22; banyak VPS memakai port kustom, mis. 20316)
.\backend\deploy\deploy_from_windows.ps1 -Server "root@IP_VPS" -Port <PORT_SSH>
```

Atau langsung di VPS:
```bash
sudo bash backend/deploy/deploy.sh          # auto-deteksi IP publik
# atau: sudo bash backend/deploy/deploy.sh 123.45.67.89
```

Hasilnya:
- Backend API : `https://api.<IP_VPS>.sslip.io`
- Admin Panel : `https://admin.<IP_VPS>.sslip.io`

### B. Sudah punya domain

```powershell
.\backend\deploy\deploy_from_windows.ps1 -Server "root@IP_VPS" -Port <PORT_SSH> -HostName "domainku.com" -Email "admin@domainku.com"
```
```bash
sudo bash backend/deploy/deploy.sh domainku.com admin@domainku.com
```
Pastikan A record `api.domainku.com` dan `admin.domainku.com` sudah mengarah ke IP VPS.

> Script ini **idempotent**: aman dijalankan ulang untuk update. Saat pertama dijalankan, script membuat secret acak dan **menampilkan password admin panel** — simpan password itu. File `.env` dan database **tidak** ditimpa pada re-run.

### Troubleshooting koneksi SSH

- **`Permission denied (publickey)` saat `ssh user@IP`** → hampir selalu **port SSH salah**. Coba `ssh -p <PORT> user@IP`. Banyak VPS memakai port kustom (mis. `20316`), bukan 22. Selalu sertakan `-Port <PORT>` pada `deploy_from_windows.ps1` (dan `-P <PORT>` pada `scp`).
- **`scp: subsystem request failed` / `Connection closed`** → server tidak menyediakan SFTP; script otomatis beralih ke protokol SCP lama (`scp -O`).
- **Diminta password berkali-kali** → normal (tiap `ssh`/`scp` meminta sekali). Pasang kunci SSH agar tidak diminta lagi: `ssh-copy-id -p <PORT> user@IP` (Windows: `type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh -p <PORT> user@IP "cat >> ~/.ssh/authorized_keys"`).

Langkah manual di bawah tetap disediakan bila kamu ingin mengontrol tiap tahap.

---


## 1. Persiapan VPS

### 1.1 Buat DNS Record

Arahkan dua subdomain ke IP VPS-mu:

| Subdomain | Arahkan ke | Gunakan untuk |
|---|---|---|
| `api.DEGOFOOD.example.com` | IP VPS | Backend API + mobile app |
| `admin.DEGOFOOD.example.com` | IP VPS | Admin panel web |

> Ganti `DEGOFOOD.example.com` dengan domain milikmu.
>
> **Belum punya domain?** Pakai **sslip.io**: `api.<IP_VPS>.sslip.io` dan `admin.<IP_VPS>.sslip.io` — tanpa beli domain, HTTPS tetap otomatis. Cara termudah: jalankan `deploy.sh` tanpa argumen (lihat bagian *Cara Cepat*).

### 1.2 Login ke VPS dan Install Dependency

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git curl
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

### 1.3 Copy Project ke VPS

Dari mesin Windows (PowerShell di folder repo):

```powershell
# -P = port SSH (HURUF BESAR; berbeda dari -p milik ssh)
scp -r -P <PORT_SSH> <REPO>/backend user@<IP_VPS>:/tmp/DEGOFOOD_backend
scp -r -P <PORT_SSH> <REPO>/admin_panel user@<IP_VPS>:/tmp/DEGOFOOD_admin
```

Kemudian di VPS:

```bash
sudo mkdir -p /opt/DEGOFOOD
sudo mv /tmp/DEGOFOOD_backend /opt/DEGOFOOD/backend
sudo mv /tmp/DEGOFOOD_admin /opt/DEGOFOOD/admin_panel
sudo chown -R www-data:www-data /opt/DEGOFOOD
```

---

## 2. Deploy Backend

### 2.1 Setup Virtual Environment

```bash
cd /opt/DEGOFOOD/backend
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -U pip
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### 2.2 Buat File Environment

```bash
sudo -u www-data cp .env.example .env
sudo -u www-data nano .env
```

Contoh minimal `.env`:

```env
DATABASE_URL=sqlite:///./food_delivery.db
ADMIN_API_KEY=super-secret-admin-key
CORS_ORIGINS=https://admin.DEGOFOOD.example.com,https://api.DEGOFOOD.example.com
```

### 2.3 Install Systemd Service

```bash
sudo cp /opt/DEGOFOOD/backend/deploy/DEGOFOOD-backend.service /etc/systemd/system/DEGOFOOD-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now DEGOFOOD-backend
sudo systemctl status DEGOFOOD-backend
```

Verifikasi:

```bash
curl http://127.0.0.1:8000/api/health
```

### 2.4 Isi Data Awal (Seed)

```bash
cd /opt/DEGOFOOD/backend
sudo -u www-data venv/bin/python seed.py
```

Perintah ini mengisi 2 restoran contoh, 8 menu, dan 1 pelanggan. Aman dijalankan berulang (hanya mengisi bila tabel masih kosong).

> **Catatan `.env`:** aplikasi membaca konfigurasi dari *environment*, bukan otomatis dari file `.env`. Saat dijalankan lewat systemd, `.env` dimuat karena `EnvironmentFile=` di unit service. Jika kamu menjalankan `uvicorn` manual tanpa systemd, ekspor dulu variabelnya, mis. `set -a; . ./.env; set +a`.

---


## 3. Deploy Admin Panel

### 3.1 Setup Virtual Environment

```bash
cd /opt/DEGOFOOD/admin_panel
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -U pip
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### 3.2 Buat File Environment

```bash
sudo -u www-data cp .env.example .env
sudo -u www-data nano .env
```

Contoh minimal:

```env
BACKEND_URL=http://127.0.0.1:8000
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password-kuat
ADMIN_API_KEY=super-secret-admin-key
SESSION_SECRET=random-secret-untuk-session
```

> `ADMIN_API_KEY` **harus sama persis** dengan yang ada di `backend/.env`, jika tidak admin panel gagal memuat data admin.

### 3.3 Install Systemd Service

```bash
sudo cp /opt/DEGOFOOD/backend/deploy/DEGOFOOD-admin.service /etc/systemd/system/DEGOFOOD-admin.service
sudo systemctl daemon-reload
sudo systemctl enable --now DEGOFOOD-admin
sudo systemctl status DEGOFOOD-admin
```

---

## 4. Reverse Proxy + HTTPS

### 4A. Menggunakan Caddy (Rekomendasi)

Edit Caddyfile:

```bash
sudo cp /opt/DEGOFOOD/backend/deploy/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile
```

Ganti domain, lalu reload:

```bash
sudo systemctl reload caddy
sudo systemctl status caddy
```

Caddy akan otomatis dapatkan sertifikat HTTPS dari Let's Encrypt.

### 4B. Menggunakan Nginx + Certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp /opt/DEGOFOOD/backend/deploy/nginx.conf /etc/nginx/sites-available/DEGOFOOD
sudo ln -s /etc/nginx/sites-available/DEGOFOOD /etc/nginx/sites-enabled/DEGOFOOD
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d api.DEGOFOOD.example.com -d admin.DEGOFOOD.example.com
```

---

## 5. Verifikasi Deployment

| Endpoint | URL Publik |
|---|---|
| Backend API | `https://api.DEGOFOOD.example.com` |
| Admin Panel | `https://admin.DEGOFOOD.example.com` |

Test dari mesin lokal:

```bash
curl https://api.DEGOFOOD.example.com/api/health
curl -H "X-Admin-Key: super-secret-admin-key" https://api.DEGOFOOD.example.com/api/admin/summary
```

---

## 6. Rebuild APK Mobile

### 6.1 Update Default URL (Opsional)

Edit `mobile_app/main.py`:

```python
API_BASE_URL = 'https://api.DEGOFOOD.example.com'
```

### 6.2 Build APK

Di PowerShell di folder `<REPO>\mobile_app`:

```powershell
.\build_apk.ps1 -ApiUrl "https://api.DEGOFOOD.example.com"

# Tanpa domain (pakai sslip.io) — ganti <IP_VPS> dengan IP VPS-mu:
# .\build_apk.ps1 -ApiUrl "https://api.<IP_VPS>.sslip.io"
```

Hasil APK akan ada di `mobile_app\build\outputs\` (mis. `FoodGo-arm64-v8a-release.apk`) dan/atau `mobile_app\build\flutter\build\app\outputs\flutter-apk\app-release.apk`.

### 6.3 Catatan Penting untuk Mobile

- APK yang sudah dideploy tetap bisa mengubah URL backend dari dalam aplikasi melalui tombol **gear/settings** di Welcome Page atau Home Page.
- Jika user mengganti URL, nilai baru akan disimpan di local storage HP.
- HTTPS wajib untuk domain publik; pastikan sertifikat valid agar tidak ada masalah CORS/network error.

---

## 7. Maintenance

### Restart service

```bash
sudo systemctl restart DEGOFOOD-backend
sudo systemctl restart DEGOFOOD-admin
```

### Lihat log

```bash
sudo journalctl -u DEGOFOOD-backend -f
sudo journalctl -u DEGOFOOD-admin -f
```

### Backup database (SQLite)

```bash
sudo cp /opt/DEGOFOOD/backend/food_delivery.db /backup/food_delivery-$(date +%F).db
```

---

## 8. Keamanan Tambahan (Direkomendasikan)

1. **Ganti ADMIN_API_KEY** dengan string acak panjang.
2. **Gunakan password admin yang kuat** di `.env` admin panel.
3. **Batasi CORS** setelah semua frontend selesai di-deploy.
4. Pertimbangkan migrate ke PostgreSQL/MySQL kalau traffic sudah tinggi.
5. Aktifkan firewall:

```bash
sudo ufw default deny incoming
sudo ufw allow <PORT_SSH>   # port SSH VPS (mis. 20316) — JANGAN salah, atau kamu bisa terkunci!
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

