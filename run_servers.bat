@echo off
echo Starting Python Messaging Suite servers...
echo.

echo Starting Django server on port 8888...
start "Django Server" cmd /k "python manage.py runserver 0.0.0.0:8888"

echo Starting FastAPI HTTP server on port 8000...
start "FastAPI HTTP Server" cmd /k "uvicorn telegram_sync.api_sync:app --reload"

echo.
echo Both servers are starting in separate windows.
echo Django: http://localhost:8888
echo FastAPI HTTP: http://localhost:8000
echo.
echo Press any key to exit this window...
pause >nul