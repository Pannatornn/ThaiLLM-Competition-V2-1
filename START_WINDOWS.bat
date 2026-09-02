@echo off
cd /d "%~dp0"
if not exist .venv (
  echo [1/4] Creating virtual environment...
  python -m venv .venv
)
echo [2/4] Installing dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if not exist .env (
  echo [3/4] Creating .env...
  copy .env.example .env >nul
  echo กรุณาใส่ THAILLM_API_KEY ในไฟล์ .env แล้ว Save
  notepad .env
  pause
)
echo [4/4] Starting Competition App...
.venv\Scripts\python.exe -m streamlit run app.py
pause
