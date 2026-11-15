@echo off
rem Start Stellar Hub (if you installed from the zip instead of the installer)
cd /d "%~dp0"
title Stellar Hub
where py >nul 2>nul
if %errorlevel%==0 (py -3 run.py --open) else (python run.py --open)
pause
