@echo off
title Apartment Charge - Local Server
cd /d "%~dp0"
echo.
echo   Serving the apartment-charge app on your Wi-Fi ...
echo   Open the address printed below on your phone.
echo.
echo   (Chrome only offers a real "install" over https. This command uses plain
echo    http, which is enough to view and edit. For the home-screen app, see README.md)
echo.
python "%~dp0serve.py" %*
if errorlevel 1 (
  echo.
  echo   Python was not found or the server failed to start.
  echo   Install Python 3, then run this file again.
  echo.
  pause
)
