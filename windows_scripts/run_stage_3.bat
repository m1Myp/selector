@echo off
set "TOOL_DIR=%~dp0"
set WORK_DIR=%TOOL_DIR%work_dir
set MAX_SELECTED_SAMPLES=5
set MIN_SIMILARITY=95
set TIME_LIMIT_SECONDS=60
set THREADS_COUNT=4

call %TOOL_DIR%venv\Scripts\activate.bat

python %TOOL_DIR%stage3\solve_math.py --min-similarity=%MIN_SIMILARITY% --max-selected-samples=%MAX_SELECTED_SAMPLES% --threads-count=%THREADS_COUNT% --time-limit-seconds=%TIME_LIMIT_SECONDS% --work-dir=%WORK_DIR%
pause