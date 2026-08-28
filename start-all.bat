@echo off
echo Starting College RAG Assistant (Backend + Frontend)...
cd /d "%~dp0"
start "College RAG - Backend (Port 8000)" cmd /k "call "%USERPROFILE%\anaconda3\Scripts\activate.bat" college-rag-assistant && python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload"
start "College RAG - Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo Both servers launched in separate windows!
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
timeout /t 5

