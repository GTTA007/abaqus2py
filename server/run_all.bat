@echo off
setlocal enabledelayedexpansion

REM Run all .inp files in current directory, serially.
REM Usage:
REM   1) Put this file in the folder containing *.inp
REM   2) Open Abaqus Command and cd to this folder
REM   3) run_all.bat
REM
REM Optional:
REM   set ABAQUS_CPUS=8
REM   set ABAQUS_DOUBLE=OFF

if not defined ABAQUS_CPUS set ABAQUS_CPUS=4
if not defined ABAQUS_DOUBLE set ABAQUS_DOUBLE=OFF

set FOUND=0
for %%F in (*.inp) do (
  set FOUND=1
  echo.
  echo [INFO] Running %%~nF from %%~nxF ...

  if /I "%ABAQUS_DOUBLE%"=="ON" (
    call abaqus job=%%~nF input=%%~nxF cpus=%ABAQUS_CPUS% double interactive
  ) else (
    call abaqus job=%%~nF input=%%~nxF cpus=%ABAQUS_CPUS% interactive
  )

  if errorlevel 1 (
    echo [ERROR] Job %%~nF failed. Stop batch.
    exit /b 1
  )
  echo [OK] Job %%~nF finished.
)

if "%FOUND%"=="0" (
  echo [WARN] No .inp found in current directory: %CD%
  exit /b 2
)

echo.
echo [OK] All jobs finished.
exit /b 0
