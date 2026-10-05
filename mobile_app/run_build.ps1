cd d:\DEGOFOOD\mobile_app
.\build_apk.ps1 -ApiUrl "http://192.168.1.6:8000" *> build3.log
$LASTEXITCODE | Out-File build_exit.txt
