#!/usr/bin/env bash
# deploy_degofood_safe.sh - Deploy DEGOFOOD ke VPS BERSAMA (NAT, banyak app lain).
#
# Kenapa script terpisah dari deploy.sh repo:
#   - repo deploy.sh memakai port 8000/8001 + Caddy + Let's Encrypt.
#     Di VPS ini 8000/8001 SUDAH DIPAKAI app lain, dan port 80/443 dipegang
#     proxy nginx milik provider -> Caddy/sslip.io MUSTAHIL.
#   - Script ini memakai port 8020 (API) + 8021 (admin) dan TIDAK menyentuh
#     nginx, Caddy, port 80/443, atau aplikasi lain di server.
#
# Idempotent: aman dijalankan ulang. File .env dan database TIDAK ditimpa.
set -euo pipefail

API_PORT="${API_PORT:-8020}"
ADMIN_PORT="${ADMIN_PORT:-8021}"
APP_DIR="${APP_DIR:-/opt/DEGOFOOD}"
RUN_USER="www-data"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Jalankan sebagai root: sudo bash $0"
    exit 1
fi

echo "==> Sumber     : ${SRC_DIR}"
echo "==> Tujuan     : ${APP_DIR}"
echo "==> API port   : ${API_PORT}"
echo "==> Admin port : ${ADMIN_PORT}"

# 0. Pastikan port tujuan benar-benar bebas (jangan ganggu app lain).
#    Service DEGOFOOD milik kita sendiri dihentikan dulu supaya re-run tetap aman.
if command -v systemctl >/dev/null 2>&1; then
    if [[ -f /etc/systemd/system/degofood-backend.service || -f /etc/systemd/system/degofood-admin.service ]]; then
        echo "==> Menghentikan service DEGOFOOD yang lama (untuk update) ..."
        systemctl stop degofood-backend degofood-admin 2>/dev/null || true
        sleep 2
    fi
fi
if command -v ss >/dev/null 2>&1; then
    for p in "${API_PORT}" "${ADMIN_PORT}"; do
        if ss -tln | grep -q ":${p} "; then
            echo "!! Port ${p} sudah dipakai proses lain. Dibatalkan agar tidak menabrak app lain."
            ss -tlnp | grep ":${p} " || true
            exit 1
        fi
    done
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> [1/6] Paket sistem ..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip sqlite3 curl >/dev/null

echo "==> [2/6] Menyalin kode ke ${APP_DIR} ..."
mkdir -p "${APP_DIR}/data"
# .env LAMA diselamatkan dulu: folder app akan dihapus-diganti saat update,
# kalau tidak diselamatkan password admin & ADMIN_API_KEY berubah tiap deploy.
ENV_BACKUP="$(mktemp -d)"
for d in backend admin_panel; do
    [[ -f "${APP_DIR}/${d}/.env" ]] && cp "${APP_DIR}/${d}/.env" "${ENV_BACKUP}/${d}.env"
done
for d in backend admin_panel; do
    rm -rf "${APP_DIR:?}/${d}"
    cp -r "${SRC_DIR}/${d}" "${APP_DIR}/${d}"
done
for d in backend admin_panel; do
    if [[ -f "${ENV_BACKUP}/${d}.env" ]]; then
        cp "${ENV_BACKUP}/${d}.env" "${APP_DIR}/${d}/.env"
    fi
done
rm -rf "${ENV_BACKUP}"
rm -rf "${APP_DIR}/backend/venv" "${APP_DIR}/admin_panel/venv"
find "${APP_DIR}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -f "${APP_DIR}/backend/food_delivery.db" "${APP_DIR}/admin_panel/food_delivery.db" 2>/dev/null || true

echo "==> [3/6] Virtualenv + dependensi ..."
for d in backend admin_panel; do
    python3 -m venv "${APP_DIR}/${d}/venv"
    "${APP_DIR}/${d}/venv/bin/pip" install -q -U pip
    "${APP_DIR}/${d}/venv/bin/pip" install -q -r "${APP_DIR}/${d}/requirements.txt"
done

echo "==> [4/6] Konfigurasi .env ..."
NEW_SECRETS=0
if [[ ! -f "${APP_DIR}/backend/.env" ]]; then
    cat > "${APP_DIR}/backend/.env" <<EOF
DATABASE_URL=sqlite:///${APP_DIR}/data/food_delivery.db
ADMIN_API_KEY=$(openssl rand -hex 24)
CORS_ORIGINS=*
SESSION_SECRET=$(openssl rand -hex 32)
EOF
    NEW_SECRETS=1
fi
ADMIN_API_KEY="$(grep -E '^ADMIN_API_KEY=' "${APP_DIR}/backend/.env" | cut -d= -f2-)"

if [[ ! -f "${APP_DIR}/admin_panel/.env" ]]; then
    cat > "${APP_DIR}/admin_panel/.env" <<EOF
BACKEND_URL=http://127.0.0.1:${API_PORT}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | cut -c1-16)
ADMIN_API_KEY=${ADMIN_API_KEY}
SESSION_SECRET=$(openssl rand -hex 32)
EOF
    NEW_SECRETS=1
fi
chmod 600 "${APP_DIR}/backend/.env" "${APP_DIR}/admin_panel/.env"
chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}"

echo "==> [5/6] systemd service (degofood-backend, degofood-admin) ..."
cat > /etc/systemd/system/degofood-backend.service <<EOF
[Unit]
Description=DEGOFOOD Backend API
After=network.target

[Service]
Type=exec
User=${RUN_USER}
Group=${RUN_USER}
WorkingDirectory=${APP_DIR}/backend
Environment=PATH=${APP_DIR}/backend/venv/bin
EnvironmentFile=${APP_DIR}/backend/.env
ExecStart=${APP_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/degofood-admin.service <<EOF
[Unit]
Description=DEGOFOOD Admin Panel
After=network.target

[Service]
Type=exec
User=${RUN_USER}
Group=${RUN_USER}
WorkingDirectory=${APP_DIR}/admin_panel
Environment=PATH=${APP_DIR}/admin_panel/venv/bin
EnvironmentFile=${APP_DIR}/admin_panel/.env
ExecStart=${APP_DIR}/admin_panel/venv/bin/uvicorn main:app --host 0.0.0.0 --port ${ADMIN_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now degofood-backend degofood-admin >/dev/null 2>&1 || true
systemctl restart degofood-backend degofood-admin
sleep 4

echo "==> [6/6] Seed data + verifikasi ..."
if command -v sudo >/dev/null 2>&1; then
    sudo -u "${RUN_USER}" bash -c "cd ${APP_DIR}/backend && set -a && . ./.env && set +a && venv/bin/python seed.py" || echo "   (seed gagal/dilewati)"
else
    runuser -u "${RUN_USER}" -- bash -c "cd ${APP_DIR}/backend && set -a && . ./.env && set +a && venv/bin/python seed.py" || echo "   (seed gagal/dilewati)"
fi

BE_LOCAL="$(curl -s --max-time 8 "http://127.0.0.1:${API_PORT}/api/health" || echo GAGAL)"
AD_LOCAL="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "http://127.0.0.1:${ADMIN_PORT}/login" || echo GAGAL)"
IP="$(curl -fsS --max-time 8 https://api.ipify.org 2>/dev/null || echo 45.66.153.146)"

echo
echo "================= HASIL DEPLOY ================="
echo "Backend lokal : ${BE_LOCAL}"
echo "Admin  lokal  : HTTP ${AD_LOCAL}"
echo "API  publik   : http://${IP}:${API_PORT}"
echo "Admin publik  : http://${IP}:${ADMIN_PORT}"
echo "Service       : $(systemctl is-active degofood-backend) / $(systemctl is-active degofood-admin)"
if [[ "${NEW_SECRETS}" == "1" ]]; then
    echo
    echo "KREDENSIAL BARU (simpan sekarang, hanya tampil di sini):"
    echo "  Admin panel  -> user: admin"
    echo "                  password: $(grep -E '^ADMIN_PASSWORD=' "${APP_DIR}/admin_panel/.env" | cut -d= -f2-)"
    echo "  ADMIN_API_KEY: ${ADMIN_API_KEY}"
else
    echo "(kredensial lama dipertahankan: ${APP_DIR}/admin_panel/.env)"
fi
echo "==============================================="

if [[ "${BE_LOCAL}" != *"ok"* ]]; then
    echo
    echo "!! Backend belum sehat. 30 baris log terakhir:"
    journalctl -u degofood-backend -n 30 --no-pager || true
fi
