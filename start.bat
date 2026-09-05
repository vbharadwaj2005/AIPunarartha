@echo off
REM ============================================
REM  AIPunarartha - one-command launcher
REM  Starts the FastAPI backend and the dashboard
REM  Requires: .venv created with uv venv --python 3.13
REM  Run from the repo root, exactly as-is.
REM ============================================

set VENV_PY=%~dp0.venv\Scripts\python.exe

echo [*] Starting AIPunarartha API on http://localhost:8000
start "AIPunarartha API" cmd /k ""%VENV_PY%" -m uvicorn core.main:app --reload --port 8000"

echo [*] Waiting 3 seconds for the API to boot...
timeout /t 3 /nobreak >nul

echo [*] Starting the dashboard on http://localhost:8501
start "AIPunarartha Dashboard" cmd /k ""%VENV_PY%" -m streamlit run app.py"

echo.
echo =============================================
echo   AIPunarartha is running
echo   API:        http://localhost:8000
echo   Dashboard:  http://localhost:8501
echo   Docs:       http://localhost:8000/docs
echo =============================================
pause