@echo off
set TOOL_DIR=C:\Users\timm0\PycharmProjects\selector_OS
set WORK_DIR=%TOOL_DIR%
set LOOKUP_MASK=*.jfr
set HOTNESS_COMPRESSION=97
set BLOCK_COMPRESSION=true
	
python %TOOL_DIR%\stage2\build_histo.py  --block-compression=%BLOCK_COMPRESSION% --hotness-compression=%HOTNESS_COMPRESSION% --work-dir=%WORK_DIR% --lookup-mask=%LOOKUP_MASK%
pause