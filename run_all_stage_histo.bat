@echo off
set TOOL_DIR=C:\Users\timm0\PycharmProjects\selector_OS
set RUN_DIR=C:\Users\timm0\PycharmProjects\selector_OS\1
set REFERENCE_DIR=%RUN_DIR%\compare_input
set SAMPLE_DIR=%RUN_DIR%
set WORK_DIR=%TOOL_DIR%\work_dir
set LOOKUP_MASK=*.histo
set HOTNESS_COMPRESSION=100
set BLOCK_COMPRESSION=true
set MAX_SELECTED_SAMPLES=5
set MIN_SIMILARITY=95
set SAMPLE_ARTIFACT_DEPTH=2
set REFERENCE_ARTIFACT_DEPTH=1

call %TOOL_DIR%\venv\Scripts\activate.bat

python %TOOL_DIR%\stage1\find_files.py --sample-dir=%SAMPLE_DIR% --reference-dir=%REFERENCE_DIR% --work-dir=%WORK_DIR% --lookup-mask=%LOOKUP_MASK%
python %TOOL_DIR%\stage2\build_histo.py  --block-compression=%BLOCK_COMPRESSION% --hotness-compression=%HOTNESS_COMPRESSION% --work-dir=%WORK_DIR%
python %TOOL_DIR%\stage3\solve_math.py --min-similarity=%MIN_SIMILARITY% --max-selected-samples=%MAX_SELECTED_SAMPLES% --work-dir=%WORK_DIR%
python %TOOL_DIR%\stage4\postprocess.py --reference-artifact-depth=%REFERENCE_ARTIFACT_DEPTH% --sample-artifact-depth=%SAMPLE_ARTIFACT_DEPTH% --work-dir=%WORK_DIR%
pause