@echo off
title NGN Board Dashboard - Local
cd /d D:\github\ngn_board

echo ===========================================
echo [NGN Board] CMD 로컬 서버 가동 중...
echo ===========================================

:: 디버그 모드 활성화 (템플릿 변경 즉시 반영)
set FLASK_ENV=development

:: 가상환경 파이썬으로 직접 실행 (오차 없는 방식)
.\venv\Scripts\python.exe -m ngn_wep.dashboard.app

pause