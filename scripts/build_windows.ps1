param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    & $Python -m pip install . -r demo/requirements.txt "pyinstaller>=6.11,<7"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed" }
    & $Python -m PyInstaller --noconfirm --clean CZNDeckcode.spec
    if ($LASTEXITCODE -ne 0) { throw "Desktop build failed" }
    Write-Host "Desktop application: $ProjectRoot\dist\CZNDeckcode.exe"
} finally {
    Pop-Location
}
