@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" (
    echo  [ERREUR] L'environnement virtuel n'est pas configure.
    echo  Executez install.bat en premier.
    pause
    exit /b 1
)

start "" "venv\Scripts\pythonw.exe" main.py
