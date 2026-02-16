@echo off
cd /d C:\data_agent\backend
call .venv\Scripts\activate
set PYTHONPATH=C:\data_agent\backend;C:\data_agent
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
pause
