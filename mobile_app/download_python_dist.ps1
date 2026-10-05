$base = 'C:\Users\lapto\AppData\Local\Pub\Cache\hosted\pub.dev\serious_python_android-0.8.7\android\build'
New-Item -ItemType Directory -Path $base -Force | Out-Null
$abis = @('arm64-v8a', 'armeabi-v7a', 'x86_64', 'x86')
$jobs = @()
foreach ($abi in $abis) {
    $out = Join-Path $base "python-android-$abi.tar.gz"
    if (Test-Path $out) {
        Write-Host "Already exists: $out"
        continue
    }
    $url = "https://github.com/flet-dev/python-build/releases/download/v3.12/python-android-dart-3.12-$abi.tar.gz"
    Write-Host "Starting download for $abi..."
    # Run each download in a background job so they can run in parallel
    $jobs += Start-Job -Name "dl_$abi" -ScriptBlock {
        param($url, $out)
        Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -ErrorAction Stop
        Write-Host "Downloaded $out"
    } -ArgumentList $url, $out
}
if ($jobs) {
    $jobs | ForEach-Object { Write-Host "Waiting for download $($_.Name)..."; Receive-Job -Job $_ -Wait -AutoRemoveJob }
}
Write-Host "All downloads complete."
Get-ChildItem $base | Select-Object Name,Length,LastWriteTime
