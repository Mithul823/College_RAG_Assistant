@echo off
echo Starting College RAG Assistant Backend on port 8000...
cd /d "%~dp0"
call "%USERPROFILE%\anaconda3\Scripts\activate.bat" college-rag-assistant
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
pause

