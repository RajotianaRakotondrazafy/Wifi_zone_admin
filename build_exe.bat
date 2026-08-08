@echo off
setlocal
cd /d "%~dp0"
title E-Konnekta ^| Build EXE

echo.
echo  ================================================
echo    E-Konnekta  -  Compilation executable
echo  ================================================
echo.

if not exist "venv\" (
    echo  [ERREUR] Environnement virtuel absent.
    echo  Executez install.bat en premier.
    pause
    exit /b 1
)

echo  [INFO] Installation / mise a jour de PyInstaller...
call venv\Scripts\pip install pyinstaller --quiet --upgrade
echo.

echo  [INFO] Nettoyage des builds precedents...
if exist "build\" rmdir /s /q "build"
if exist "dist\E-Konnekta\" rmdir /s /q "dist\E-Konnekta"

echo  [INFO] Compilation en cours (patientez)...
call venv\Scripts\pyinstaller ekonnekta.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo  [ERREUR] La compilation a echoue. Consultez les messages ci-dessus.
    pause
    exit /b 1
)

:: Copier .env.example dans le dossier de distribution
if exist ".env.example" copy ".env.example" "dist\E-Konnekta\.env.example" >nul

echo.
echo  ================================================
echo    Build termine !
echo.
echo    Dossier de sortie : dist\E-Konnekta\
echo.
echo    Pour distribuer l'application :
echo      1. Copiez le dossier dist\E-Konnekta\ a destination
echo      2. Copiez .env.example en .env et configurez-le
echo      3. Lancez E-Konnekta.exe
echo.
echo    La base de donnees et les logs seront crees
echo    automatiquement au premier demarrage.
echo  ================================================
echo.
pause
