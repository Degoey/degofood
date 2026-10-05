$path = 'C:\Users\lapto\AppData\Local\Pub\Cache\hosted\pub.dev\serious_python_android-0.8.7\android\build.gradle'
$text = Get-Content $path -Raw
$text = $text -replace "abiFilters 'arm64-v8a'", "abiFilters 'arm64-v8a', 'armeabi-v7a', 'x86_64'"
Set-Content -Path $path -Value $text -NoNewline
Write-Host "Restored abiFilters"
Select-String -Path $path -Pattern 'abiFilters'

