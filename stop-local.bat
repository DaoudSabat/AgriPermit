@echo off
echo Stopping services...
taskkill /FI "WindowTitle eq AgriPermit API*" /F
taskkill /FI "WindowTitle eq AgriPermit Web*" /F
echo Services stopped!
pause
