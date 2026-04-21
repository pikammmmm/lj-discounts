@echo off
setlocal
cd /d "%~dp0"

lj-discounts.exe --open
set EXITCODE=%ERRORLEVEL%

echo.
if "%EXITCODE%"=="0" (
  echo Done. The report is offers.html in this folder.
) else (
  echo LJ Discounts failed with exit code %EXITCODE%.
  echo Check your internet connection and try again.
)
pause
exit /b %EXITCODE%
