@echo off
set TOOL_DIR=C:\Users\timm0\PycharmProjects\selector_OS
set WORK_DIR=%TOOL_DIR%\work_dir
set MAX_SELECTED_SAMPLES=5
set MIN_SIMILARITY=95
	
call %TOOL_DIR%\venv\Scripts\activate.bat

python %TOOL_DIR%\stage3\solve_math.py --min-similarity=%MIN_SIMILARITY% --max-selected-samples=%MAX_SELECTED_SAMPLES% --work-dir=%WORK_DIR%
pause