@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHON=python
where python >nul 2>&1
if errorlevel 1 set PYTHON=py
where %PYTHON% >nul 2>&1
if errorlevel 1 goto nopython
echo Installing required packages ...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt
echo.
echo Done. Now run run.bat to generate the report.
echo.
pause
exit /b 0

:nopython
echo.
echo [ERROR] Python not found. Please install Python 3.9+ from https://www.python.org/downloads/
echo.
pause
exit /b 1
