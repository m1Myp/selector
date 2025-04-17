@echo off
set RUN_DIR=C:\Users\timm0\PycharmProjects\selector_OS\1
set REFERENCE_DIR=%RUN_DIR%\compare_input
set SAMPLE_DIR=%RUN_DIR%
set LOOKUP_MASK=*.histop

python stage1/find_files.py
pause
