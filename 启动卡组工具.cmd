@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
where py >nul 2>nul
if errorlevel 1 (
  python scripts\desktop_entry.py
) else (
  py -3 scripts\desktop_entry.py
)
if errorlevel 1 pause
