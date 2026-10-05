# Build script untuk membuat APK DEGOFOOD (Flet)
# Jalankan dari dalam folder mobile_app
# Contoh: .\build_apk.ps1 -ApiUrl "http://192.168.1.6:8000"
param(
    [string]$ApiUrl = "http://192.168.1.6:8000"
)

$ErrorActionPreference = "Stop"

# Pastikan kita berada di folder mobile_app
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Sesuaikan jalur SDK/lokasi tools jika diperlukan
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot"
$env:ANDROID_SDK_ROOT = "$env:LOCALAPPDATA\Android\Sdk"
$env:ANDROID_HOME = $env:ANDROID_SDK_ROOT
# Hindari UnicodeEncodeError saat flet/rich menulis karakter seperti ✅ ke konsol
$env:PYTHONIOENCODING = "utf-8"
# Pastikan output Python langsung ditulis ke log agar dapat dipantau
$env:PYTHONUNBUFFERED = "1"

# Pastikan Flutter tersedia di PATH (jika diinstal di D:\flutter)
if (Test-Path "D:\flutter\bin\flutter.bat") {
    $env:PATH = "D:\flutter\bin;" + $env:PATH
}


Write-Host "JAVA_HOME: $env:JAVA_HOME"
Write-Host "ANDROID_SDK_ROOT: $env:ANDROID_SDK_ROOT"
Write-Host "API_BASE_URL akan dipakai: $ApiUrl"

# Cek apakah Developer Mode aktif (dibutuhkan Flutter untuk membuat symlink plugin)
try {
    $devMode = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" -Name "AllowDevelopmentWithoutDeveloperLicense" -ErrorAction Stop
    $devModeEnabled = $devMode.AllowDevelopmentWithoutDeveloperLicense -eq 1
} catch {
    $devModeEnabled = $false
}

if (-not $devModeEnabled) {
    Write-Host "" -ForegroundColor Red
    Write-Host "BUILD GAGAL: Windows Developer Mode belum diaktifkan." -ForegroundColor Red
    Write-Host "Flutter membutuhkan symlink support untuk membangun APK dengan plugin." -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "Cara mengaktifkan Developer Mode:" -ForegroundColor Yellow
    Write-Host "  1. Tekan Win + I untuk membuka Settings." -ForegroundColor Yellow
    Write-Host "  2. Pilih Privacy & security > For developers." -ForegroundColor Yellow
    Write-Host "  3. Aktifkan 'Developer Mode'." -ForegroundColor Yellow
    Write-Host "  4. Jalankan ulang PowerShell/Terminal, lalu jalankan kembali script ini." -ForegroundColor Yellow
    Write-Host "" -ForegroundColor Red
    Write-Host "Atau jalankan PowerShell sebagai Administrator lalu jalankan:" -ForegroundColor Yellow
    Write-Host "  reg add `"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock`" /v AllowDevelopmentWithoutDeveloperLicense /t REG_DWORD /d 1 /f" -ForegroundColor Yellow
    exit 1
}

# Update API_BASE_URL di main.py sesuai parameter
$mainPath = Join-Path $scriptDir "main.py"
$mainContent = Get-Content $mainPath -Raw
$mainContent = $mainContent -replace "API_BASE_URL = .*", "API_BASE_URL = '$ApiUrl'"
Set-Content -Path $mainPath -Value $mainContent -NoNewline

# Pastikan compileSdk tertinggi agar plugin native-assets tidak gagal
$buildGradle = Join-Path $scriptDir "build\flutter\android\app\build.gradle"
if (Test-Path $buildGradle) {
    (Get-Content $buildGradle -Raw) -replace 'compileSdkVersion\s+flutter\.compileSdkVersion', 'compileSdk 35' | Set-Content -Path $buildGradle -NoNewline
}

# Build APK
& ".\venv\Scripts\flet.exe" "build" "apk" "--project" "DEGOFOOD" "--org" "com.degofood" "--description" "Aplikasi pemesanan makanan DEGOFOOD" "--verbose" "--no-rich-output" "."

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build selesai. Cek folder build\apk untuk hasilnya." -ForegroundColor Green
} else {
    Write-Host "Build gagal. Periksa pesan error di atas." -ForegroundColor Red
    exit $LASTEXITCODE
}
