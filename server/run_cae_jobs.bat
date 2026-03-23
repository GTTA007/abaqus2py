@echo off
setlocal

REM One-click flow:
REM   1) export all jobs from a .cae to .inp files
REM   2) run all exported .inp files serially
REM
REM Usage:
REM   run_cae_jobs.bat D:\path\to\model.cae D:\path\to\inp_out
REM
REM Optional before running:
REM   set ABAQUS_CPUS=8
REM   set ABAQUS_DOUBLE=ON

if "%~1"=="" (
  echo [ERROR] Missing CAE path.
  echo Usage: run_cae_jobs.bat ^<cae_path^> ^<out_dir^>
  exit /b 2
)

if "%~2"=="" (
  echo [ERROR] Missing output directory.
  echo Usage: run_cae_jobs.bat ^<cae_path^> ^<out_dir^>
  exit /b 2
)

set "CAE_PATH=%~1"
set "OUT_DIR=%~2"
set "SCRIPT_DIR=%~dp0"

echo [INFO] CAE file: %CAE_PATH%
echo [INFO] Output dir: %OUT_DIR%
echo [INFO] Exporting all jobs to .inp ...

call abaqus cae noGUI="%SCRIPT_DIR%write_all_inp.py" -- --cae "%CAE_PATH%" --out-dir "%OUT_DIR%"
if errorlevel 1 (
  echo [ERROR] Failed to export .inp files from CAE.
  exit /b 1
)

echo [INFO] Running exported .inp files serially ...
pushd "%OUT_DIR%"
call "%SCRIPT_DIR%run_all.bat"
set "RUN_ERR=%ERRORLEVEL%"
popd

if not "%RUN_ERR%"=="0" (
  echo [ERROR] Batch run failed with code %RUN_ERR%.
  exit /b %RUN_ERR%
)

echo [OK] Export and serial run finished.
exit /b 0
