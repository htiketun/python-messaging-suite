@echo off
echo Starting Python Messaging Suite servers...
echo.

echo Starting Django server on port 8888...
start "Django Server" cmd /k "python manage.py runserver --port 8888"

echo Starting FastAPI WebSocket server on port 6666...
start "FastAPI WebSocket Server" cmd /k "uvicorn telegram_sync.telegram_sync_ws:app --reload --port 6666"

echo.
echo Both servers are starting in separate windows.
echo Django: http://localhost:8888
echo FastAPI WebSocket: http://localhost:6666
echo.
echo Press any key to exit this window...
pause >nul