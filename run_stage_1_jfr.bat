@echo off
set RUN_DIR=C:\Users\timm0\PycharmProjects\selector_OS\jfr_07_04_ksj\1-1-1
set REFERENCE_DIR=%RUN_DIR%\compare_input
set SAMPLE_DIR=%RUN_DIR%
set LOOKUP_MASK=*.jfr

python stage1/find_files.py
pause
