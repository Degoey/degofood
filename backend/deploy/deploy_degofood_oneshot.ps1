# deploy_degofood_oneshot.ps1
# Upload DEGOFOOD ke VPS lalu deploy -- AMAN untuk VPS BERSAMA (NAT).
# Pakai port 8020 (API) + 8021 (admin). Tidak menyentuh nginx, Caddy,
# port 80/443, maupun aplikasi lain di server.
#
# Cara pakai (PowerShell, di folder repo D:\DEGOFOOD):
#   .\backend\deploy\deploy_degofood_oneshot.ps1
#
# Uji tanpa upload (hanya buat arsip + tampilkan script remote):
#   .\backend\deploy\deploy_degofood_oneshot.ps1 -DryRun
#
# Password SSH akan diminta 2x (sekali upload, sekali deploy).
# Kalau username bukan root: -Server "namauser@45.66.153.146"

param(
    [string]$Server    = "root@45.66.153.146",
    [int]$SshPort      = 20316,
    [int]$ApiPort      = 8020,
    [int]$AdminPort    = 8021,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot  = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$tarFile   = Join-Path $env:TEMP "degofood-deploy.tar.gz"
$remoteDir = "/tmp/degofood-deploy"

function Invoke-Native {
    param([string]$FilePath, [string[]]$Arguments)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $FilePath @Arguments
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    if ($code -ne 0) { throw "Perintah '$FilePath' gagal (exit $code)." }
}

$sshOpts = @("-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=20")

# WAJIB pakai tar bawaan Windows (bsdtar). GNU tar dari Git/MSYS salah membaca
# path "D:\DEGOFOOD" sebagai nama host remote ("Cannot connect to D:").
$tarExe = Join-Path $env:SystemRoot "System32\tar.exe"
if (-not (Test-Path $tarExe)) { $tarExe = "tar" }
$repoUnix = $repoRoot -replace '\\', '/'

# Script yang dijalankan di VPS (dikirim lewat stdin, jadi bebas masalah quoting)
$remoteScript = @"
set -e
rm -rf $remoteDir/src
mkdir -p $remoteDir/src
tar -xzf $remoteDir/degofood.tar.gz -C $remoteDir/src
cd $remoteDir/src
API_PORT=$ApiPort ADMIN_PORT=$AdminPort bash backend/deploy/deploy_degofood_safe.sh
"@

Write-Host "==> [1/4] Membuat arsip dari $repoRoot ..."
if (Test-Path $tarFile) { Remove-Item $tarFile -Force }
Invoke-Native $tarExe @("-czf", $tarFile,
    "--exclude=venv", "--exclude=__pycache__", "--exclude=.env",
    "--exclude=*.db", "--exclude=*.log",
    "-C", $repoUnix, "backend", "admin_panel")
Write-Host ("    arsip: {0:N1} KB" -f ((Get-Item $tarFile).Length / 1KB))

if ($DryRun) {
    Write-Host ""
    Write-Host "==> DRY RUN: tidak mengunggah apa pun. Script yang akan dijalankan di VPS:"
    Write-Host "-------------------------------------------------------------"
    Write-Host $remoteScript
    Write-Host "-------------------------------------------------------------"
    Write-Host "Arsip siap : $tarFile"
    Write-Host ("Target     : {0} port {1} (API {2} / admin {3})" -f $Server, $SshPort, $ApiPort, $AdminPort)
    exit 0
}

Write-Host "==> [2/4] Upload ke ${Server}:${remoteDir} -- masukkan password SSH sekarang ..."
Invoke-Native "ssh" (@("-p", "$SshPort") + $sshOpts + @($Server, "mkdir -p $remoteDir"))
Invoke-Native "scp" (@("-O", "-P", "$SshPort") + $sshOpts + @($tarFile, "${Server}:${remoteDir}/degofood.tar.gz"))

Write-Host "==> [3/4] Deploy di VPS -- masukkan password SSH sekali lagi ..."
$remoteFile = Join-Path $env:TEMP "degofood-remote.sh"
[System.IO.File]::WriteAllText($remoteFile, $remoteScript.Replace("`r`n", "`n"), (New-Object System.Text.ASCIIEncoding))
Get-Content $remoteFile -Raw | & ssh -p $SshPort @sshOpts $Server "sudo bash -s"
if ($LASTEXITCODE -ne 0) { throw "Deploy di VPS gagal (exit $LASTEXITCODE)." }

Write-Host "==> [4/4] Selesai."
Write-Host "    API   : http://45.66.153.146:$ApiPort/api/health"
Write-Host "    Admin : http://45.66.153.146:$AdminPort"
Write-Host "    (password admin tercetak di blok KREDENSIAL BARU pada output di atas)"
