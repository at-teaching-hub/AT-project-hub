@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHON=python
where python >nul 2>&1
if errorlevel 1 set PYTHON=py
if "%~1"=="" goto usage
echo School year 2025-26, Quarter 1 (Sep-Dec 2025)
%PYTHON% src\main.py --file "%~1" --type 季報 --season 1 --year 2025
echo.
pause
exit /b 0

:usage
echo Drag and drop your maintenance file onto this .bat file, or run:
echo   run_example.bat "C:\path\to\file.xlsx"
echo.
pause
exit /b 1
