# Catatan Deploy DEGOFOOD — server hermes-agent-1025

Dibuat oleh Hermes. Terakhir diperbarui: 2026-10-08.

## Status

Aplikasi **sudah jalan** di server ini sebagai container Docker.

| Bagian | Alamat internal | Container |
|---|---|---|
| Backend API | http://127.0.0.1:8000 | `degofood-backend` |
| Admin Panel | http://127.0.0.1:8001 | `degofood-admin` |

Keduanya **hanya bind ke 127.0.0.1** — tidak bisa diakses langsung dari internet.
Ini disengaja: akses publik harus lewat reverse proxy.

## Cara mengelola

```bash
cd /root/apps/degofood

docker compose ps                    # status
docker compose logs -f backend       # log backend
docker compose logs -f admin         # log admin
docker compose restart backend       # restart
docker compose up -d --build         # rebuild setelah kode berubah
docker compose down                  # matikan
```

Update kode dari GitHub:

```bash
cd /root/apps/degofood
git pull
docker compose up -d --build
```

## Data & konfigurasi

- Database SQLite: `/root/apps/degofood/data/food_delivery.db` (volume, aman saat rebuild)
- Kredensial: `backend/.env` dan `admin_panel/.env` — **tidak ikut ke git** (sudah di .gitignore)
- `ADMIN_API_KEY` di kedua file **harus sama persis**, kalau tidak admin panel gagal memuat data

Backup database:

```bash
cp /root/apps/degofood/data/food_delivery.db \
   /root/backup/degofood-$(date +%F).db
```

## Kenapa belum bisa diakses publik

Server ini memakai **IP bersama** milik provider (vpsmurah). Hasil pengujian:

- Port **80** dari internet dijawab oleh **proxy provider**, bukan server kita.
  Balasannya: *"Domain belum terhubung ke VPS"*.
- Port lain (8000, 8001, 8080, dst) **tidak bisa diakses dari internet** sama sekali.

**Yang perlu dilakukan pemilik VPS:** daftarkan domain di panel
`my.vpsmurah.co.id` → **VPS Saya** → **Domain & Website**.

Setelah domain terdaftar dan mengarah ke VPS ini, pasang reverse proxy (Caddy)
yang listen di port 80 dan meneruskan berdasarkan Host header:

- `api.<domain>` → `127.0.0.1:8000`
- `admin.<domain>` → `127.0.0.1:8001`

## Catatan keamanan

- `CORS_ORIGINS=*` masih terbuka. Batasi ke domain asli setelah domain terdaftar.
- Password admin panel dibuat acak oleh Hermes — **ganti** setelah login pertama.
- Mobile app (`mobile_app/`) belum dibangun. Isi `API_BASE_URL` di `main.py`
  dengan URL publik backend sebelum build APK.
- Jangan pernah menjalankan `backend/deploy/deploy.sh` di server ini: skrip itu
  memasang nginx/caddy langsung ke host dan menimpa konfigurasi sistem.
  Deploy di sini memakai Docker (lihat `docker-compose.yml`).
