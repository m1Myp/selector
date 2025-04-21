@echo off
set TOOL_DIR=C:\Users\timm0\PycharmProjects\selector_OS
set RUN_DIR=C:\Users\timm0\PycharmProjects\selector_OS\1
set REFERENCE_DIR=%RUN_DIR%\compare_input
set SAMPLE_DIR=%RUN_DIR%
set WORK_DIR=%TOOL_DIR%
set LOOKUP_MASK=*.histop

python %TOOL_DIR%\stage1\find_files.py --sample-dir=%SAMPLE_DIR% --reference-dir=%REFERENCE_DIR% --work-dir=%WORK_DIR% --lookup-mask=%LOOKUP_MASK%
pause
