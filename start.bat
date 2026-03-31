@echo off
echo Starting AgriPermit services...
docker-compose up -d
echo.
echo Services started!
echo   - API: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo   - MinIO Console: http://localhost:9001
echo.
echo View logs: docker-compose logs -f
pause
