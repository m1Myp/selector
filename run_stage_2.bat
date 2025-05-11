@echo off
set TOOL_DIR=C:\Users\timm0\PycharmProjects\selector_OS
set WORK_DIR=%TOOL_DIR%\work_dir
set HOTNESS_COMPRESSION=100
set BLOCK_COMPRESSION=true
	
python %TOOL_DIR%\stage2\build_histo.py  --block-compression=%BLOCK_COMPRESSION% --hotness-compression=%HOTNESS_COMPRESSION% --work-dir=%WORK_DIR%
pause