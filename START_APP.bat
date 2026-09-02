@echo off
cd /d "%~dp0"

echo ===============================
echo ThaiLLM Academic Intelligence
echo Integrated WWWW UI + AI Backend
echo ===============================

if not exist .venv (
  python -m venv .venv
)

.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install fastapi uvicorn

if not exist .env (
  copy .env.example .env >nul
  echo Please add THAILLM_API_KEY in .env
  notepad .env
  pause
)

if exist frontend (
  cd frontend
  if not exist node_modules (
    npm install
  )
  npm run build
  cd ..
)

start "ThaiLLM API" cmd /k ".venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000"

start http://localhost:8000

echo Started.
pause
