# DEGOFOOD Merchant (aplikasi merchant, Flet)

Aplikasi Android (dan desktop) untuk merchant DEGOFOOD. Dibuat dengan Flet 0.25.2,
satu file besar `main.py` sebagai entry point, dan seluruh data diambil dari REST API
backend DEGOFOOD (`https://degofood.my.id`). Tidak ada data contoh/dummy di dalam kode.

## 1. Menjalankan di desktop (untuk uji cepat)

```bash
cd merchant_app
python -m venv venv
# Windows
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py
# Linux/macOS
venv/bin/pip install -r requirements.txt
venv/bin/python main.py
```

Jalankan sebagai web app (tanpa Flutter) untuk memeriksa tampilan:

```bash
# Linux/macOS
DEGOFOOD_PORT=8560 venv/bin/python main.py
# Windows PowerShell
$env:DEGOFOOD_PORT=8560; venv\Scripts\python main.py
# lalu buka http://127.0.0.1:8560
```

Login memakai akun merchant yang sudah diverifikasi admin (nomor HP atau email +
password pilihan merchant sendiri). Merchant yang belum punya akun memakai tombol
**Daftar** di layar login: isi nama, HP/email, dan password, lalu kirim. Akun **belum
aktif** sampai admin DEGOFOOD memverifikasi pendaftaran dan menautkan restoran.

## 2. Build APK di laptop Windows

Prasyarat: Python 3.10+, Flutter SDK (mis. `D:\flutter`), Android SDK
(`%LOCALAPPDATA%\Android\Sdk`), JDK 21, dan **Windows Developer Mode aktif**
(Flutter butuh symlink; skrip akan berhenti dengan instruksi bila belum aktif).

```powershell
cd merchant_app
python -m venv venv
venv\Scripts\pip install -r requirements.txt
.\build_apk.ps1                                  # pakai https://degofood.my.id
.\build_apk.ps1 -ApiUrl "https://staging.degofood.my.id"
```

Skrip akan: mengecek Developer Mode, menyetel `JAVA_HOME`/`ANDROID_SDK_ROOT`/PATH Flutter,
mengganti baris `API_BASE_URL` di `main.py` sesuai `-ApiUrl`, lalu menjalankan
`flet build apk --project degofoodmerchant --org id.degofood`.
Hasil APK ada di `build\apk\`.

Alamat server juga bisa diganti dari dalam aplikasi: **Lainnya > Server** (ada tombol
"Uji koneksi" ke `/api/health`). Alamat non-https (selain localhost/127.0.0.1) ditolak,
supaya APK tidak pernah menembak IP LAN seperti bug di aplikasi pelanggan.

## 3. Fitur yang tersedia

- **Login**: identitas (HP/email) + password, tombol **Daftar** untuk pendaftaran mandiri
  merchant (akun baru dipakai setelah admin memverifikasi), auto-login saat aplikasi dibuka ulang
  (divalidasi ke `/api/merchant/me`, 401 kembali ke layar login), pesan error server
  (401/429/422) ditampilkan apa adanya.
- **Beranda**: kartu sambutan + badge Buka/Tutup + tombol cepat buka/tutup toko,
  4 kartu statistik, grafik batang 7 hari (dibuat dari Container, tanpa library chart),
  5 menu terlaris, kartu saldo tersedia + jumlah settlement, tarik-untuk-refresh.
- **Pesanan**: filter Aktif/Semua/Selesai/Dibatalkan, daftar kartu pesanan, halaman detail
  (rincian item, alamat, catatan, telepon pelanggan bisa ditekan untuk disalin,
  tombol aksi hanya dari `allowed_next_status`, dialog konfirmasi untuk pembatalan,
  timeline riwayat dari `/events`).
- **Menu**: pencarian, filter kategori, kartu menu dengan foto (`image_url`) atau ikon,
  badge Habis/stok, tombol + (FAB) untuk tambah, form tambah/ubah (nama, deskripsi, harga,
  kategori, URL foto, stok, switch tersedia), hapus dengan konfirmasi, dan tombol cepat
  on/off ketersediaan langsung dari daftar.
- **Keuangan**: kartu saldo tersedia, baris "ditahan pengajuan" dan "total ledger",
  tab Ringkasan | Riwayat | Pencairan | Rekening, riwayat ledger (hijau + / merah -),
  pengajuan pencairan (jumlah + rekening, `client_ref` uuid acak), daftar pengajuan
  dengan status + catatan admin, tambah/hapus rekening, dan unduh laporan CSV
  (pilih rentang tanggal, file disimpan lalu path + tombol salin isi CSV ditampilkan).
- **Lainnya**: profil toko (deskripsi, jam buka/tutup, minimum order, terima pesanan,
  buka/tutup toko) + Simpan; Promo (CRUD lengkap); Notifikasi (polling 20 detik saat
  aplikasi terbuka, kursor disimpan di client storage); Server (ganti alamat + uji
  koneksi); Keluar.

## 4. Keterbatasan jujur

- **Promo belum diterapkan di checkout pelanggan.** Backend mengembalikan
  `applied_at_checkout = false`; promo hanya tercatat di sisi merchant. Catatan ini juga
  ditampilkan di UI.
- **Pencairan manual lewat admin.** Tidak ada payout otomatis. Alur status:
  `pending` -> `approved` -> `paid` (admin transfer manual ke rekening merchant).
- **Saldo bukan uang yang langsung bisa ditarik.** Saldo bertambah hanya setelah admin
  memverifikasi settlement per pesanan. Aplikasi tidak pernah menampilkan saldo sebagai
  "siap dicairkan" tanpa catatan ini.
- **Notifikasi hanya polling foreground.** Aplikasi memeriksa pesanan baru tiap 20 detik
  **saat aplikasi dibuka**; tidak ada push notification background.
- **APK ditandatangani debug key.** Hasil `flet build apk` default memakai debug signing,
  jadi belum layak untuk Google Play Store (perlu keystore rilis + `--sign`/`--keystore`).
- **Pendaftaran mandiri.** Merchant mendaftar sendiri dari layar login (nama, HP/email,
  password pilihannya, data toko) lewat `POST /api/merchant/auth/register`. Akun dibuat
  admin saat verifikasi; sebelum diverifikasi, login ditolak dengan pesan "menunggu
  verifikasi admin". Rate limit: maksimal 5 pendaftaran/jam per IP dan jeda 30 detik
  antar pendaftaran.
- **CSV disimpan ke folder dokumen aplikasi/temp**, lalu ditampilkan path-nya; berbagi
  file antar aplikasi belum diimplementasikan (hanya path + salin isi ke clipboard).
- Uji render/browser di server build: lihat catatan di laporan proyek; pengujian APK nyata
  tetap harus dilakukan di perangkat/laptop Windows dengan Flutter SDK.
