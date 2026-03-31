@echo off
REM AgriPermit Setup WITHOUT Docker
REM For systems that can't run Docker

echo ========================================
echo   AgriPermit Setup (No Docker)
echo ========================================
echo.

REM Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found!
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Prerequisites found
echo.

REM Create project directory
set PROJECT_DIR=C:\Projects\AgriPermit
if not exist "%PROJECT_DIR%" mkdir "%PROJECT_DIR%"
cd /d "%PROJECT_DIR%"

echo [Step 1/4] Creating project structure...
mkdir apps\api 2>nul
mkdir apps\web\src 2>nul
mkdir packages 2>nul

REM Create API files
echo [Step 2/4] Creating API...
(
echo fastapi==0.104.1
echo uvicorn[standard]==0.24.0
echo sqlalchemy==2.0.23
echo pydantic==2.5.0
) > apps\api\requirements.txt

(
echo from fastapi import FastAPI
echo from fastapi.middleware.cors import CORSMiddleware
echo.
echo app = FastAPI^(title="AgriPermit API"^)
echo.
echo app.add_middleware^(
echo     CORSMiddleware,
echo     allow_origins=["*"],
echo     allow_credentials=True,
echo     allow_methods=["*"],
echo     allow_headers=["*"]
echo ^)
echo.
echo @app.get^("/")
echo async def root^(^):
echo     return {"message": "AgriPermit API", "status": "running"}
echo.
echo @app.get^("/health"^)
echo async def health^(^):
echo     return {"status": "healthy"}
echo.
echo @app.get^("/api/v1/parcels"^)
echo async def get_parcels^(^):
echo     return {"parcels": [{"id": "test_1", "address": "Jerusalem Test"}]}
) > apps\api\main.py

echo Installing Python packages...
cd apps\api
python -m pip install -r requirements.txt
cd ..\..

REM Create Web App
echo [Step 3/4] Creating Web App...
cd apps\web

(
echo {
echo   "name": "agripermit-web",
echo   "version": "1.0.0",
echo   "type": "module",
echo   "scripts": {
echo     "dev": "vite",
echo     "build": "vite build"
echo   },
echo   "dependencies": {
echo     "react": "^18.2.0",
echo     "react-dom": "^18.2.0"
echo   },
echo   "devDependencies": {
echo     "@vitejs/plugin-react": "^4.2.0",
echo     "vite": "^5.0.0"
echo   }
echo }
) > package.json

(
echo import { defineConfig } from 'vite'
echo import react from '@vitejs/plugin-react'
echo export default defineConfig^({ plugins: [react^(^)] }^)
) > vite.config.js

(
echo ^<!DOCTYPE html^>
echo ^<html lang="he" dir="rtl"^>
echo ^<head^>
echo   ^<meta charset="UTF-8" /^>
echo   ^<meta name="viewport" content="width=device-width, initial-scale=1.0" /^>
echo   ^<title^>AgriPermit^</title^>
echo ^</head^>
echo ^<body^>
echo   ^<div id="root"^>^</div^>
echo   ^<script type="module" src="/src/main.jsx"^>^</script^>
echo ^</body^>
echo ^</html^>
) > index.html

mkdir src 2>nul
(
echo import React from 'react'
echo import ReactDOM from 'react-dom/client'
echo import App from './App'
echo ReactDOM.createRoot^(document.getElementById^('root'^)^).render^(^<App /^>^)
) > src\main.jsx

(
echo import React from 'react'
echo function App^(^) {
echo   return ^(
echo     ^<div style={{padding: '20px', textAlign: 'center'}}^>
echo       ^<h1^>🌾 AgriPermit^</h1^>
echo       ^<h2^>עגרי-פרמיט^</h2^>
echo       ^<p^>Agricultural Land Permits System^</p^>
echo     ^</div^>
echo   ^)
echo }
echo export default App
) > src\App.jsx

echo Installing npm packages...
call npm install

cd ..\..

REM Create Mobile App
echo [Step 4/4] Creating Mobile App...
echo This may take a few minutes...
call npx create-expo-app@latest AgriPermitMobile --template blank --yes

REM Create start scripts
(
echo @echo off
echo echo Starting AgriPermit API...
echo cd apps\api
echo start "AgriPermit API" python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
echo cd ..\..
echo echo.
echo echo API running at: http://localhost:8000
echo echo API Docs: http://localhost:8000/docs
echo echo.
echo timeout /t 3 /nobreak ^>nul
echo echo Starting Web App...
echo cd apps\web
echo start "AgriPermit Web" npm run dev
echo cd ..\..
echo echo.
echo echo Web app running at: http://localhost:5173
echo echo.
echo echo Both services started!
echo pause
) > start-local.bat

(
echo @echo off
echo echo Stopping services...
echo taskkill /FI "WindowTitle eq AgriPermit API*" /F
echo taskkill /FI "WindowTitle eq AgriPermit Web*" /F
echo echo Services stopped!
echo pause
) > stop-local.bat

REM Create README
(
echo # AgriPermit - No Docker Setup
echo.
echo ## Start Services
echo ```
echo start-local.bat
echo ```
echo.
echo This will start:
echo - API: http://localhost:8000
echo - Web: http://localhost:5173
echo.
echo ## Mobile App
echo ```
echo cd AgriPermitMobile
echo npm install
echo npx expo start
echo ```
echo.
echo Scan QR code with Expo Go app on your phone
echo.
echo ## Stop Services
echo ```
echo stop-local.bat
echo ```
) > README.md

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Your project is at: %PROJECT_DIR%
echo.
echo To start:
echo   1. Run: start-local.bat
echo   2. Open: http://localhost:8000
echo   3. Open: http://localhost:5173
echo.
echo For mobile:
echo   cd AgriPermitMobile
echo   npm install
echo   npx expo start
echo.
pause