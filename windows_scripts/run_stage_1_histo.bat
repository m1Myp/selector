@echo off
set "TOOL_DIR=%~dp0"
set RUN_DIR=%TOOL_DIR%1
set REFERENCE_DIR=%RUN_DIR%\compare_input
set SAMPLE_DIR=%RUN_DIR%
set WORK_DIR=%TOOL_DIR%work_dir
set LOOKUP_MASK=*.histo

call %TOOL_DIR%venv\Scripts\activate.bat

python %TOOL_DIR%stage1\find_files.py --sample-dir=%SAMPLE_DIR% --reference-dir=%REFERENCE_DIR% --work-dir=%WORK_DIR% --lookup-mask=%LOOKUP_MASK%
pause
