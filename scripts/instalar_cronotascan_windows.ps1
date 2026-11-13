# Instala e testa o CronotaScan no Windows (Univali / laboratório).
# Uso: clique direito > Executar com PowerShell, ou:
#   powershell -ExecutionPolicy Bypass -File .\scripts\instalar_cronotascan_windows.ps1

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Raiz

Write-Host "=== CronotaScan — instalacao ===" -ForegroundColor Cyan
Write-Host "Pasta: $Raiz"

function Get-PythonCmd {
    foreach ($cmd in @("python", "py")) {
        try {
            $v = & $cmd -c "import sys; print(sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $parts = $v -replace "[() ]", "" -split ","
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                    return $cmd
                }
            }
        } catch { }
    }
    return $null
}

$py = Get-PythonCmd
if (-not $py) {
    Write-Host "ERRO: Python 3.11+ nao encontrado. Instale Python ou use o PC do laboratorio." -ForegroundColor Red
    exit 1
}
Write-Host "Python: $py" -ForegroundColor Green

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Criando ambiente virtual .venv ..."
    & $py -m venv .venv
}

$venvPy = Join-Path $Raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "ERRO: .venv nao foi criado." -ForegroundColor Red
    exit 1
}

Write-Host "Instalando dependencias (pode demorar no OpenCV) ..."
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt

Write-Host "Testando imports ..."
& $venvPy -c "import fastapi, cv2, sqlalchemy, reportlab; print('OK imports')"

Write-Host ""
Write-Host "=== Instalacao concluida ===" -ForegroundColor Green
Write-Host "Para iniciar o sistema, execute:" -ForegroundColor Yellow
Write-Host "  .\scripts\iniciar_cronotascan.bat"
Write-Host "Ou:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\python.exe main.py"
Write-Host "Depois abra no navegador: http://127.0.0.1:8081/" -ForegroundColor Yellow
