@echo off
echo Starting AgriPermit API...
cd apps\api
start "AgriPermit API" python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd ..\..
echo.
echo API running at: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
timeout /t 3 /nobreak >nul
echo Starting Web App...
cd apps\web
start "AgriPermit Web" npm run dev
cd ..\..
echo.
echo Web app running at: http://localhost:5173
echo.
echo Both services started!
pause
