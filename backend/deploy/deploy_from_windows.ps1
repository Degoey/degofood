# deploy_from_windows.ps1 - Upload repo ke VPS lalu jalankan deploy.sh di sana.
#
# Contoh tanpa domain (otomatis pakai <IP>.sslip.io + HTTPS):
#   .\deploy_from_windows.ps1 -Server "root@45.66.153.146" -Port 20316
#
# Contoh dengan domain:
#   .\deploy_from_windows.ps1 -Server "root@45.66.153.146" -Port 20316 -HostName "domainku.com" -Email "admin@domainku.com"
#
# PENTING: -Port adalah port SSH VPS. Banyak VPS memakai port kustom (mis. 20316),
#          BUKAN 22. Salah port -> "Permission denied (publickey)" atau "Connection refused".
#
# Prasyarat di Windows: OpenSSH client (perintah `ssh` dan `scp`) tersedia.
# Tips: agar tidak diminta password berulang, pasang kunci SSH di VPS
#       (`ssh-copy-id -p <PORT> user@IP`), lalu pakai -IdentityFile bila perlu.
param(
    [Parameter(Mandatory = $true)][string]$Server,   # user@IP_VPS, mis. root@45.66.153.146
    [int]$Port = 22,                                 # port SSH VPS (mis. 20316)
    [string]$HostName = "",                          # domain dasar atau IP; kosong = auto-deteksi di VPS
    [string]$Email = "",                             # opsional, untuk notifikasi Let's Encrypt
    [string]$IdentityFile = "",                      # opsional, path private key SSH
    [switch]$SkipPreflight                           # lewati uji koneksi SSH (hemat 1x prompt password)
)

$ErrorActionPreference = "Stop"

# --- Helper: jalankan perintah native; JANGAN jadikan stderr ssh/scp sebagai error fatal ---
function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'   # cegah stderr (mis. "Permanently added host") jadi NativeCommandError
    try {
        & $FilePath @Arguments
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    if ($code -ne 0) {
        throw "Perintah '$FilePath $($Arguments -join ' ')' gagal (exit code $code)."
    }
}

# Repo root = dua level di atas folder script ini (backend/deploy -> root)
$repoRoot  = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$remoteDir = "/tmp/foodgo"

# Opsi SSH umum: terima host key baru otomatis (hindari prompt "yes/no") + timeout wajar
$sshOpts = @("-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")
if ($IdentityFile) { $sshOpts += @("-i", $IdentityFile) }

Write-Host "Repo   : $repoRoot"
Write-Host "Server : $Server"
Write-Host "Port   : $Port"
Write-Host "Host   : $(if ($HostName) { $HostName } else { '(auto-deteksi IP di VPS)' })"

# --- Preflight: uji koneksi SSH agar error port/user terlihat jelas sejak awal ---
if (-not $SkipPreflight) {
    Write-Host "`n==> Menguji koneksi SSH ke $Server (port $Port) ..."
    try {
        Invoke-Native "ssh" (@("-p", "$Port") + $sshOpts + @($Server, "echo OK"))
    } catch {
        Write-Host ""
        Write-Host "GAGAL terhubung ke SSH. Periksa:" -ForegroundColor Red
        Write-Host "  - Port SSH benar? Banyak VPS memakai port kustom (mis. -Port 20316), bukan 22." -ForegroundColor Yellow
        Write-Host "  - User & IP benar? (mis. root@45.66.153.146)" -ForegroundColor Yellow
        Write-Host "  - Password/kunci SSH benar?" -ForegroundColor Yellow
        throw
    }
}

# --- Kemas kode (tanpa venv/__pycache__/.env/db) ---
Write-Host "`n==> Mengemas kode (tanpa venv/__pycache__/.env/db) ..."
$tarFile = Join-Path $env:TEMP "foodgo-deploy.tar.gz"
if (Test-Path $tarFile) { Remove-Item $tarFile -Force }
Invoke-Native "tar" @("-czf", $tarFile, "--exclude=venv", "--exclude=__pycache__", "--exclude=.env", "--exclude=*.db", "-C", $repoRoot, "backend", "admin_panel")

# --- Upload (otomatis fallback ke protokol SCP lama bila server tanpa SFTP) ---
Write-Host "==> Mengunggah ke VPS ..."
$scpOpts = @("-P", "$Port") + $sshOpts
try {
    Invoke-Native "scp" ($scpOpts + @($tarFile, "$Server`:$remoteDir.tar.gz"))
} catch {
    Write-Host "scp gagal, mencoba protokol SCP lama (-O) ..." -ForegroundColor Yellow
    Invoke-Native "scp" (@("-O") + $scpOpts + @($tarFile, "$Server`:$remoteDir.tar.gz"))
}

# --- Ekstrak + jalankan deploy.sh dalam SATU sesi SSH (hemat prompt password) ---
Write-Host "==> Mengekstrak & menjalankan deploy.sh di VPS ..."
$argList = @()
if ($HostName) { $argList += "'$HostName'" } elseif ($Email) { $argList += "''" }
if ($Email) { $argList += "'$Email'" }
$argStr = $argList -join ' '
$remoteCmd = "rm -rf $remoteDir && mkdir -p $remoteDir && tar -xzf $remoteDir.tar.gz -C $remoteDir && rm -f $remoteDir.tar.gz && sudo bash $remoteDir/backend/deploy/deploy.sh $argStr"
Invoke-Native "ssh" (@("-p", "$Port") + $sshOpts + @($Server, $remoteCmd))
Remove-Item $tarFile -Force

Write-Host "`nSelesai. Cek status di VPS: curl http://127.0.0.1:8000/api/health" -ForegroundColor Green
