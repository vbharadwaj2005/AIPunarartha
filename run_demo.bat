@echo off
REM ============================================
REM  AIPunarartha — One-command demo launcher
REM  Starts FastAPI backend + Streamlit dashboard
REM  Requires: .venv created via uv venv --python 3.13
REM ============================================

set VENV_PY=%~dp0.venv\Scripts\python.exe

echo [*] Starting AIPunarartha backend on http://localhost:8000
start "AIPunarartha API" cmd /k "cd backend && "%VENV_PY%" -m uvicorn app.main:app --reload --port 8000"

echo [*] Waiting 3 seconds for FastAPI to boot...
timeout /t 3 /nobreak >nul

echo [*] Starting Streamlit dashboard on http://localhost:8501
start "AIPunarartha Dashboard" cmd /k "cd dashboard && "%VENV_PY%" -m streamlit run app.py"

echo.
echo =============================================
echo   AIPunarartha is running
echo   Backend:  http://localhost:8000
echo   Dashboard: http://localhost:8501
echo   API Docs: http://localhost:8000/docs
echo =============================================
pause
