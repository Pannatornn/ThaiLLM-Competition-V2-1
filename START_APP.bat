@echo off
cd /d "%~dp0"

echo =====================================
echo ThaiLLM Academic Intelligence
 echo WWWW UI + ThaiLLM Backend
echo =====================================

if not exist .venv (
  echo Creating Python environment...
  python -m venv .venv
)

.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
  echo Please add THAILLM_API_KEY in .env
  notepad .env
  pause
)

start "ThaiLLM API" cmd /k ".venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000"

timeout /t 4 >nul
start http://localhost:8000

echo Application started.
pause
