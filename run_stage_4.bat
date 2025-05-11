@echo off
set TOOL_DIR=C:\Users\timm0\PycharmProjects\selector_OS
set WORK_DIR=%TOOL_DIR%\work_dir
set SAMPLE_ARTIFACT_DEPTH=2
set REFERENCE_ARTIFACT_DEPTH=1

python %TOOL_DIR%\stage4\postprocess.py --reference-artifact-depth=%REFERENCE_ARTIFACT_DEPTH% --sample-artifact-depth=%SAMPLE_ARTIFACT_DEPTH% --work-dir=%WORK_DIR%
pause