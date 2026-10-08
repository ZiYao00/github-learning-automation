@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish-ods-v22-preview.ps1"
if errorlevel 1 (
  echo.
  echo Publish failed; existing files were not overwritten.
) else (
  echo.
  echo V2.2 preview publishing finished.
)
pause
