# DEGOFOOD Mobile App

Aplikasi mobile DEGOFOOD dibangun dengan [Flet](https://flet.dev/) (Python + Flutter) untuk memesan makanan dari restoran yang terhubung ke backend DEGOFOOD.

## Fitur

- Melihat daftar restoran yang sedang buka
- Melihat menu restoran dan menambahkan ke keranjang
- Keranjang belanja dengan biaya pengiriman otomatis
- Riwayat pesanan pelanggan
- Navigasi bottom bar (Home / Cart / Orders)

## Struktur File

- `main.py` — kode utama aplikasi Flet
- `requirements.txt` — dependensi Python
- `build_apk.ps1` — script PowerShell untuk build APK Android
- `venv/` — virtual environment Python

## Menjalankan di Desktop (Development)

1. Pastikan backend DEGOFOOD sudah berjalan (default: `http://127.0.0.1:8000`).
2. Aktifkan virtual environment:

   ```powershell
   .\venv\Scripts\activate
   ```

3. Jalankan aplikasi:

   ```powershell
   flet run main.py
   ```

## Build APK Android

1. Pastikan sudah terinstall:
   - Flutter SDK
   - Android SDK
   - JDK 17 atau 21
   - Windows **Developer Mode** aktif (dibutuhkan untuk symlink plugin Flutter)

2. Jalankan script build:

   ```powershell
   cd d:\DEGOFOOD\mobile_app
   .\build_apk.ps1 -ApiUrl "http://<IP_LAN>:8000"
   ```

   Ganti `<IP_LAN>` dengan IP lokal komputer yang menjalankan backend, contoh: `http://192.168.1.6:8000`.

3. Setelah build selesai, APK hasil build berada di:

   ```
   d:\DEGOFOOD\mobile_app\build\flutter\build\app\outputs\flutter-apk\app-release.apk
   ```

   Atau sesuai output dari Flet.

## Troubleshooting

- **UnicodeEncodeError saat build**: script sudah mengatur `PYTHONIOENCODING=utf-8` untuk mencegah error karakter ✅.
- **"Building with plugins requires symlink support"**: aktifkan Windows Developer Mode melalui Settings (`Privacy & security > For developers > Developer Mode`), atau jalankan perintah registry sebagai admin.
- **Tidak bisa terhubung ke backend**: pastikan perangkat Android dan komputer backend berada dalam satu jaringan WiFi, dan gunakan IP LAN komputer backend saat build, bukan `127.0.0.1`.
