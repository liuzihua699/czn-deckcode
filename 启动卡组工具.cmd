@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
where py >nul 2>nul
if errorlevel 1 (
  python -m czn_deckcode ui
) else (
  py -3 -m czn_deckcode ui
)
if errorlevel 1 pause
