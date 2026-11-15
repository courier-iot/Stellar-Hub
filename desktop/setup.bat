@echo off
rem Stellar Hub setup: checks your hardware and drivers and picks an AI model
cd /d "%~dp0"
title Stellar Hub setup
where py >nul 2>nul
if %errorlevel%==0 (py -3 setup_hub.py --pause) else (python setup_hub.py --pause)
