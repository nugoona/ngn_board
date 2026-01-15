@echo off
title NGN Board Dashboard - Local
cd /d D:\github\ngn_board

echo ===========================================
echo [NGN Board] Local Server Starting...
echo ===========================================

:: Enable debug mode
set FLASK_ENV=development

:: Run with venv python
.\venv\Scripts\python.exe -m ngn_wep.dashboard.app

pause
