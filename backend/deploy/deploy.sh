#!/usr/bin/env bash
#
# deploy.sh - Deploy DEGOFOOD (backend + admin panel) ke VPS Ubuntu.
#
# Pemakaian (jalankan sebagai root, dari root repo):
#   sudo bash backend/deploy/deploy.sh                 # auto-deteksi IP publik -> pakai <IP>.sslip.io
#   sudo bash backend/deploy/deploy.sh 123.45.67.89    # pakai 123.45.67.89.sslip.io
#   sudo bash backend/deploy/deploy.sh domainku.com    # pakai api.domainku.com & admin.domainku.com
#
# Skrip ini idempotent: aman dijalankan ulang untuk memperbarui aplikasi.
# Yang TIDAK ditimpa saat re-run: file .env dan database (secret tetap).
set -euo pipefail

ARG="${1:-}"
ADMIN_EMAIL="${2:-}"

is_ip() { [[ "${1:-}" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; }
detect_ip() {
    curl -fsS --max-time 8 https://api.ipify.org 2>/dev/null \
        || curl -fsS --max-time 8 https://ifconfig.me 2>/dev/null \
        || true
}

if [[ -z "${ARG}" ]]; then
    ARG="$(detect_ip)"
    if [[ -z "${ARG}" ]]; then
        echo "Tidak bisa mendeteksi IP publik. Jalankan: sudo bash $0 <IP_ATAU_DOMAIN>"
        exit 1
    fi
fi

if is_ip "${ARG}"; then
    # Tanpa domain: pakai sslip.io (HTTPS tetap otomatis via Let's Encrypt)
    API_DOMAIN="api.${ARG}.sslip.io"
    ADMIN_DOMAIN="admin.${ARG}.sslip.io"
    echo "==> Mode tanpa domain: memakai sslip.io"
else
    API_DOMAIN="api.${ARG}"
    ADMIN_DOMAIN="admin.${ARG}"
fi

if [[ "${EUID}" -ne 0 ]]; then
    echo "Jalankan sebagai root: sudo bash $0 ${ARG}"
    exit 1
fi


APP_DIR="/opt/DEGOFOOD"
DATA_DIR="${APP_DIR}/data"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUN_USER="www-data"

echo "==> Repo sumber : ${SRC_ROOT}"
echo "==> API domain  : ${API_DOMAIN}"
echo "==> Admin domain: ${ADMIN_DOMAIN}"

# 1. Paket sistem
echo "==> [1/8] Memasang paket sistem ..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip rsync curl openssl >/dev/null
if ! command -v caddy >/dev/null 2>&1; then
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https >/dev/null
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -y
    apt-get install -y caddy >/dev/null
fi

# 2. Salin kode (tanpa venv/__pycache__/.env/db)
echo "==> [2/8] Menyalin kode ke ${APP_DIR} ..."
mkdir -p "${APP_DIR}"
rsync -a --exclude venv --exclude __pycache__ --exclude '.env' --exclude '*.db' \
    "${SRC_ROOT}/backend/" "${APP_DIR}/backend/"
rsync -a --exclude venv --exclude __pycache__ --exclude '.env' \
    "${SRC_ROOT}/admin_panel/" "${APP_DIR}/admin_panel/"
mkdir -p "${DATA_DIR}"

# 3. venv + dependencies
echo "==> [3/8] Membuat virtualenv & memasang dependencies ..."
for sub in backend admin_panel; do
    [[ -d "${APP_DIR}/${sub}/venv" ]] || python3 -m venv "${APP_DIR}/${sub}/venv"
    "${APP_DIR}/${sub}/venv/bin/pip" install -U pip >/dev/null
    "${APP_DIR}/${sub}/venv/bin/pip" install -r "${APP_DIR}/${sub}/requirements.txt" >/dev/null
done

# 4. Secret + .env (hanya dibuat sekali)
echo "==> [4/8] Menyiapkan .env & secret acak ..."
if [[ ! -f "${APP_DIR}/backend/.env" ]]; then
    ADMIN_API_KEY="$(openssl rand -hex 32)"
    cat > "${APP_DIR}/backend/.env" <<EOF
DATABASE_URL=sqlite:///${DATA_DIR}/food_delivery.db
ADMIN_API_KEY=${ADMIN_API_KEY}
CORS_ORIGINS=https://${API_DOMAIN},https://${ADMIN_DOMAIN}
SESSION_SECRET=$(openssl rand -hex 32)
EOF
else
    ADMIN_API_KEY="$(grep -E '^ADMIN_API_KEY=' "${APP_DIR}/backend/.env" | cut -d= -f2-)"
fi

if [[ ! -f "${APP_DIR}/admin_panel/.env" ]]; then
    ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | cut -c1-16)"
    cat > "${APP_DIR}/admin_panel/.env" <<EOF
BACKEND_URL=http://127.0.0.1:8000
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMIN_PASSWORD}
ADMIN_API_KEY=${ADMIN_API_KEY}
SESSION_SECRET=$(openssl rand -hex 32)
EOF
    echo "    !! Login admin panel -> user: admin | password: ${ADMIN_PASSWORD}  (SIMPAN!)"
fi

chmod 600 "${APP_DIR}/backend/.env" "${APP_DIR}/admin_panel/.env" 2>/dev/null || true
chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}"

# 5. Seed data awal
echo "==> [5/8] Mengisi data awal (seed) ..."
sudo -u "${RUN_USER}" bash -c "cd ${APP_DIR}/backend && set -a && . ./.env && set +a && venv/bin/python seed.py"

# 6. systemd
echo "==> [6/8] Memasang systemd service ..."
install -m 644 "${APP_DIR}/backend/deploy/DEGOFOOD-backend.service" /etc/systemd/system/DEGOFOOD-backend.service
install -m 644 "${APP_DIR}/backend/deploy/DEGOFOOD-admin.service" /etc/systemd/system/DEGOFOOD-admin.service
systemctl daemon-reload
systemctl enable --now DEGOFOOD-backend DEGOFOOD-admin

# 7. Reverse proxy Caddy
echo "==> [7/8] Menulis konfigurasi Caddy ..."
CADDY_HEADER=""
if [[ "${ADMIN_EMAIL}" == *@*.* ]]; then
    CADDY_HEADER="{ email ${ADMIN_EMAIL} }"
    echo "    (email ACME: ${ADMIN_EMAIL})"
fi
cat > /etc/caddy/Caddyfile <<EOF
${CADDY_HEADER}
${API_DOMAIN} {
    reverse_proxy 127.0.0.1:8000
}

${ADMIN_DOMAIN} {
    reverse_proxy 127.0.0.1:8001
}
EOF
systemctl reload caddy 2>/dev/null || systemctl restart caddy

# 8. Verifikasi
echo "==> [8/8] Verifikasi ..."
sleep 2
echo "Backend lokal : $(curl -s http://127.0.0.1:8000/api/health || echo GAGAL)"
echo "Admin lokal   : HTTP $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/login || echo GAGAL)"
echo
echo "Selesai. Setelah DNS mengarah ke VPS, uji dari luar:"
echo "  curl https://${API_DOMAIN}/api/health"
echo "  Buka https://${ADMIN_DOMAIN} (login pakai kredensial di atas)"
