@echo off
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao instalado. Execute primeiro:
    echo   powershell -ExecutionPolicy Bypass -File scripts\instalar_cronotascan_windows.ps1
    pause
    exit /b 1
)
echo CronotaScan — servidor em http://127.0.0.1:8081/
echo Feche esta janela para parar o servidor.
".venv\Scripts\python.exe" main.py
pause
