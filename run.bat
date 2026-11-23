@echo off
setlocal
if /i "%~1"=="--console" goto :launch
start "AI Project" "%ComSpec%" /d /k call "%~f0" --console
exit /b
:launch
cd /d "%~dp0" || goto :failed
echo Starting AI Project...
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv || goto :failed
)
if exist ".venv\installed-requirements.txt" (
  fc /b backend\requirements.txt .venv\installed-requirements.txt >nul
  if not errorlevel 1 goto :serve
)
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || goto :failed
copy /y backend\requirements.txt .venv\installed-requirements.txt >nul || goto :failed
:serve
".venv\Scripts\python.exe" scripts\start_studio.py
if errorlevel 1 goto :failed
exit /b 0
:failed
echo Startup stopped. The error is printed above.
exit /b 1
