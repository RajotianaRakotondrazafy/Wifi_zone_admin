@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title E-Konnekta ^| Installation

echo.
echo  ================================================
echo    E-Konnekta  -  Installation
echo  ================================================
echo.

:: ── Verifier Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo  Telechargez Python 3.10+ sur https://www.python.org/downloads/
    echo  Cochez "Add Python to PATH" pendant l'installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)
if !PYMAJ! LSS 3 goto :python_trop_vieux
if !PYMAJ! EQU 3 if !PYMIN! LSS 10 goto :python_trop_vieux
goto :python_ok

:python_trop_vieux
echo  [ERREUR] Python 3.10 ou superieur requis.
echo  Version detectee : !PYVER!
pause
exit /b 1

:python_ok
echo  [OK] Python !PYVER! detecte.
echo.

:: ── Creer l'environnement virtuel ────────────────────────────────────────────
if not exist "venv\" (
    echo  [INFO] Creation de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERREUR] Echec de la creation de l'environnement virtuel.
        pause
        exit /b 1
    )
    echo  [OK] Environnement virtuel cree.
) else (
    echo  [OK] Environnement virtuel existant detecte.
)
echo.

:: ── Installer les dependances ─────────────────────────────────────────────────
echo  [INFO] Installation des dependances (peut prendre 2-3 minutes)...
call venv\Scripts\pip install --upgrade pip --quiet
call venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERREUR] Echec de l'installation des dependances.
    echo  Verifiez votre connexion internet et relancez install.bat.
    pause
    exit /b 1
)
echo  [OK] Dependances installees.
echo.

:: ── Creer le fichier .env si absent ──────────────────────────────────────────
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo  [OK] Fichier .env cree depuis .env.example.
        echo       Modifiez .env pour personaliser la configuration.
    ) else (
        (
            echo APP_NAME=WiFi Zone
            echo APP_ENV=production
        ) > .env
        echo  [OK] Fichier .env minimal cree.
    )
) else (
    echo  [OK] Fichier .env existant conserve.
)
echo.

:: ── Initialiser la base de donnees ───────────────────────────────────────────
echo  [INFO] Initialisation de la base de donnees...
call venv\Scripts\python -c "import sys; sys.path.insert(0,'.'); from database.connection import DatabaseConnection; from database.init_db import initialiser_base; DatabaseConnection(); initialiser_base()"
if errorlevel 1 (
    echo  [ERREUR] Echec de l'initialisation de la base de donnees.
    pause
    exit /b 1
)
echo  [OK] Base de donnees initialisee.
echo.

:: ── Creer le compte administrateur par defaut ────────────────────────────────
echo  [INFO] Verification du compte administrateur...
call venv\Scripts\python scripts\creer_admin.py
echo.

echo  ================================================
echo    Installation terminee avec succes !
echo.
echo    Identifiants par defaut :
echo      Login    : admin@wifizone.mg
echo      Mot de passe : admin123
echo.
echo    IMPORTANT : Changez le mot de passe apres
echo    la premiere connexion !
echo.
echo    Pour lancer l'application : double-cliquez
echo    sur lancer.bat
echo  ================================================
echo.
pause
