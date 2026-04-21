@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0refresh.ps1"
set EXITCODE=%ERRORLEVEL%

if not "%EXITCODE%"=="0" (
  echo.
  echo LJ Discounts failed with exit code %EXITCODE%.
  pause
)
exit /b %EXITCODE%
