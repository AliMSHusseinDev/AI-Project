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
start "AI Project API" ".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --port 8000
pushd frontend
echo Open http://localhost:5173 when Vite reports ready.
call npm run dev -- --host 127.0.0.1
popd
exit /b
:failed
echo Setup failed. Check the Python 3.12 and Node.js installations and the message above.
pause
exit /b 1
