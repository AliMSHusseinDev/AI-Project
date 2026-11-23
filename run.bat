@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv || goto :failed
)
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || goto :failed
pushd frontend
call npm ci --no-audit --no-fund
if errorlevel 1 (popd & goto :failed)
popd
if not exist outputs mkdir outputs
"%~dp0.venv\Scripts\python.exe" scripts\start_studio.py || goto :failed
exit /b
:failed
echo Setup failed. Check the Python 3.12 and Node.js installations and the message above.
pause
exit /b 1
