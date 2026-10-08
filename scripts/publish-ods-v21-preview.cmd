@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish-ods-v21-preview.ps1"
if errorlevel 1 (
  echo.
  echo Publish failed; no existing file was overwritten.
) else (
  echo.
  echo Preview publishing finished.
)
pause
