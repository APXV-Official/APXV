@echo off
set PORT=5500
set URL=http://127.0.0.1:%PORT%/

echo.
echo  APXV1 site preview
echo  ------------------
echo  URL: %URL%
echo.
echo  Press Ctrl+C to stop the server.
echo.

cd /d "%~dp0"
start "" "%URL%"
py -3 -m http.server %PORT% --bind 127.0.0.1