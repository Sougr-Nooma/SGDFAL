@echo off
setlocal
cd /d "%~dp0"
echo Demarrage de l installation SGD...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-SGD.ps1"
set "installExitCode=%ERRORLEVEL%"
if not "%installExitCode%"=="0" (
    echo.
    echo L installation a echoue avec le code %installExitCode%.
    echo Lisez le message ci-dessus, puis contactez le support.
    pause
    exit /b %installExitCode%
)
exit /b 0
