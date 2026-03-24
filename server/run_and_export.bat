@echo off
setlocal

REM One-click server flow:
REM   1) export all jobs from a .cae to .inp files
REM   2) run all exported .inp files serially
REM   3) export CSV data from a selected .odb
REM
REM Usage:
REM   run_and_export.bat ^<cae_path^> ^<out_dir^> ^<job_name^> ^<step^> ^<disp_node_set^> ^<reaction_node_sets^> [disp_u] [reaction_rf] [frame]

if "%~1"=="" (
  echo [ERROR] Missing CAE path.
  exit /b 2
)

if "%~2"=="" (
  echo [ERROR] Missing output directory.
  exit /b 2
)

if "%~3"=="" (
  echo [ERROR] Missing job name.
  exit /b 2
)

if "%~4"=="" (
  echo [ERROR] Missing step name.
  exit /b 2
)

if "%~5"=="" (
  echo [ERROR] Missing displacement node set.
  exit /b 2
)

if "%~6"=="" (
  echo [ERROR] Missing reaction node sets.
  exit /b 2
)

set "CAE_PATH=%~1"
set "OUT_DIR=%~2"
set "JOB_NAME=%~3"
set "STEP_NAME=%~4"
set "DISP_NODE_SET=%~5"
set "REACTION_NODE_SETS=%~6"
set "DISP_U=%~7"
set "REACTION_RF=%~8"
set "FRAME=%~9"

if "%DISP_U%"=="" set "DISP_U=U2"
if "%REACTION_RF%"=="" set "REACTION_RF=RF2"
if "%FRAME%"=="" set "FRAME=-1"

set "SCRIPT_DIR=%~dp0"
set "CSV_DIR=%OUT_DIR%\csv\%JOB_NAME%"
set "ODB_PATH=%OUT_DIR%\%JOB_NAME%.odb"

echo [INFO] CAE file: %CAE_PATH%
echo [INFO] Output dir: %OUT_DIR%
echo [INFO] Job name: %JOB_NAME%
echo [INFO] Step name: %STEP_NAME%
echo [INFO] Displacement node set: %DISP_NODE_SET%
echo [INFO] Reaction node sets: %REACTION_NODE_SETS%

call "%SCRIPT_DIR%run_cae_jobs.bat" "%CAE_PATH%" "%OUT_DIR%"
if errorlevel 1 (
  echo [ERROR] Failed to generate or run jobs.
  exit /b 1
)

if not exist "%ODB_PATH%" (
  echo [ERROR] ODB file not found: %ODB_PATH%
  exit /b 3
)

if not exist "%CSV_DIR%" mkdir "%CSV_DIR%"

echo [INFO] Exporting CSV from %ODB_PATH% ...
call abaqus python "%SCRIPT_DIR%export_abaqus_data.py" -- --odb "%ODB_PATH%" --step "%STEP_NAME%" --disp-node-set "%DISP_NODE_SET%" --reaction-node-sets "%REACTION_NODE_SETS%" --disp-u "%DISP_U%" --reaction-rf "%REACTION_RF%" --frame "%FRAME%" --out-dir "%CSV_DIR%"
if errorlevel 1 (
  echo [ERROR] Failed to export CSV data.
  exit /b 4
)

echo [OK] Server run and export finished.
echo [OK] CSV dir: %CSV_DIR%
exit /b 0
