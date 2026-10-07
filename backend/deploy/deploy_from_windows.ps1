# deploy_from_windows.ps1 - Upload repo ke VPS lalu jalankan deploy.sh.
#
# Contoh tanpa domain (auto pakai <IP>.sslip.io + HTTPS):
#   .\deploy_from_windows.ps1 -Server "root@123.45.67.89"
#
# Contoh dengan domain:
#   .\deploy_from_windows.ps1 -Server "root@123.45.67.89" -HostName "domainku.com" -Email "admin@domainku.com"
#
# Prasyarat di Windows: OpenSSH client (perintah `ssh` dan `scp`) tersedia.
param(
    [Parameter(Mandatory = $true)][string]$Server,   # user@IP_VPS, mis. root@123.45.67.89
    [string]$HostName = "",                          # domain dasar atau IP; kosong = auto-deteksi di VPS
    [string]$Email = ""                              # opsional, untuk notifikasi Let's Encrypt
)

$ErrorActionPreference = "Stop"

# Repo root = dua level di atas folder script ini (backend/deploy -> root)
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$remoteDir = "/tmp/foodgo"

Write-Host "Repo   : $repoRoot"
Write-Host "Server : $Server"
Write-Host "Host   : $(if ($HostName) { $HostName } else { '(auto-deteksi IP di VPS)' })"

Write-Host "`n==> Mengemas kode (tanpa venv/__pycache__/.env/db) ..."
$tarFile = Join-Path $env:TEMP "foodgo-deploy.tar.gz"
if (Test-Path $tarFile) { Remove-Item $tarFile -Force }
tar -czf $tarFile --exclude=venv --exclude=__pycache__ --exclude=.env --exclude=*.db -C $repoRoot backend admin_panel

Write-Host "==> Mengunggah & mengekstrak di VPS ..."
scp $tarFile "$Server`:$remoteDir.tar.gz"
ssh $Server "rm -rf $remoteDir && mkdir -p $remoteDir && tar -xzf $remoteDir.tar.gz -C $remoteDir && rm -f $remoteDir.tar.gz"
Remove-Item $tarFile -Force

Write-Host "==> Menjalankan deploy.sh di VPS ..."
$argList = @()
if ($HostName) { $argList += "'$HostName'" } elseif ($Email) { $argList += "''" }
if ($Email) { $argList += "'$Email'" }
$argStr = $argList -join ' '
ssh $Server "sudo bash $remoteDir/backend/deploy/deploy.sh $argStr"

Write-Host "`nSelesai. Cek status di VPS: curl http://127.0.0.1:8000/api/health" -ForegroundColor Green
