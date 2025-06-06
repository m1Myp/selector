@echo off
rmdir /s /q venv

python -m venv venv

call venv\Scripts\activate.bat

pip install --upgrade pip setuptools

pip install -r requirements.txt

pause
