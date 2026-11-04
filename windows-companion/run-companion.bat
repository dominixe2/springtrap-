@echo off
title Micro Helper Windows Companion
where py >nul 2>nul
if %errorlevel%==0 (py -3 "%~dp0companion.py") else (python "%~dp0companion.py")
pause
