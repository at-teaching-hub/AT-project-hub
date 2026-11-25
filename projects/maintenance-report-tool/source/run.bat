@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHON=python
where python >nul 2>&1
if errorlevel 1 set PYTHON=py
where %PYTHON% >nul 2>&1
if errorlevel 1 goto nopython
%PYTHON% src\main.py --interactive
echo.
pause
exit /b 0

:nopython
echo.
echo [ERROR] Python not found. Please install Python 3.9+ from https://www.python.org/downloads/
echo         Remember to tick "Add python.exe to PATH" during installation.
echo.
pause
exit /b 1
