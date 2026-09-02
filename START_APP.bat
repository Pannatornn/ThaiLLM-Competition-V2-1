@echo off
setlocal
cd /d "%~dp0"

echo =====================================
echo ThaiLLM Academic Intelligence
echo WWWW UI + ThaiLLM Backend
echo =====================================

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.11 or newer and enable Add Python to PATH.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js / npm not found. Install Node.js LTS, then run this file again.
  pause
  exit /b 1
)

if not exist .venv (
  echo [1/6] Creating Python environment...
  python -m venv .venv
  if errorlevel 1 goto :fail
)

echo [2/6] Installing Python dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if not exist .env (
  echo [3/6] Creating .env...
  copy .env.example .env >nul
  echo.
  echo Put your THAILLM_API_KEY in .env, save, then close Notepad.
  notepad .env
  pause
) else (
  echo [3/6] .env found.
)

echo [4/6] Installing frontend dependencies...
pushd frontend
if not exist node_modules (
  call npm install
  if errorlevel 1 (
    popd
    goto :fail
  )
)

echo [5/6] Building React frontend...
call npm run build
if errorlevel 1 (
  popd
  goto :fail
)
popd

echo [6/6] Starting FastAPI server...
start "ThaiLLM Academic Intelligence" cmd /k "cd /d \"%~dp0\" && .venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000"

timeout /t 5 >nul
start "" http://localhost:8000

echo.
echo Application started at http://localhost:8000
echo Health check: http://localhost:8000/api/health
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Setup or build failed. Read the error above and send it here.
pause
exit /b 1
