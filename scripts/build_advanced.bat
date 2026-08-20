@echo off
setlocal

REM Ce script vit dans scripts\, mais toutes les commandes ci-dessous
REM supposent d'etre executees depuis la racine du projet.
cd /d "%~dp0.."

echo ============================================
echo   MultiMiner - Script de compilation (avance)
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Installez Python 3.10+ depuis https://www.python.org/downloads/
    exit /b 1
)

echo.
echo [1/8] Verification / telechargement du mineur CPU...
if not exist miner mkdir miner
if not exist "miner\cpuminer-gw64-corei7.exe" (
    echo Telechargement de cpuminer-multi ^(depuis le depot officiel GitHub^)...
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\fetch_miner.ps1
    if errorlevel 1 (
        echo [ATTENTION] Le telechargement automatique du mineur CPU a echoue.
        echo Vous pourrez le faire manuellement plus tard ^(voir miner\README.txt^).
    )
) else (
    echo Mineur CPU deja present dans miner\, telechargement ignore.
)

echo.
echo [2/8] Verification / telechargement du mineur GPU...
if not exist miner\gpu mkdir miner\gpu
if not exist "miner\gpu\lolMiner.exe" (
    echo Telechargement de lolMiner ^(depuis le depot officiel GitHub^)...
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\fetch_gpu_miner.ps1
    if errorlevel 1 (
        echo [ATTENTION] Le telechargement automatique du mineur GPU a echoue.
        echo Le mode GPU pourra etre configure manuellement plus tard si besoin.
    )
) else (
    echo Mineur GPU deja present dans miner\gpu\, telechargement ignore.
)

echo.
echo [3/8] Creation de l'environnement virtuel...
if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERREUR] Impossible d'activer l'environnement virtuel.
    exit /b 1
)

echo.
echo [4/8] Installation des dependances...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances.
    exit /b 1
)

echo.
echo [5/8] Nettoyage des anciens builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [6/8] Compilation avec PyInstaller...
pyinstaller MultiMiner.spec
if errorlevel 1 (
    echo [ERREUR] La compilation a echoue. Voir le detail ci-dessus.
    exit /b 1
)

if not exist dist\MultiMiner.exe (
    echo [ERREUR] MultiMiner.exe est introuvable dans dist\ apres compilation.
    exit /b 1
)

echo.
echo [7/8] Preparation du dossier de distribution ^(icone + mineurs + desinstalleur^)...
if exist assets\icon.ico (
    copy /y assets\icon.ico dist\icon.ico >nul
)
copy /y scripts\uninstall_template.bat dist\Uninstall.bat >nul
if not exist dist\miner (
    xcopy /e /i /q miner dist\miner >nul
)
if not exist dist\config (
    xcopy /e /i /q config dist\config >nul
)

echo.
echo [8/8] Creation du raccourci sur le Bureau...
set "ICON_FOR_SHORTCUT=%CD%\dist\icon.ico"
if not exist "%ICON_FOR_SHORTCUT%" set "ICON_FOR_SHORTCUT=%CD%\dist\MultiMiner.exe"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1 -ExePath "%CD%\dist\MultiMiner.exe" -IconPath "%ICON_FOR_SHORTCUT%"
if errorlevel 1 (
    echo [ATTENTION] Le raccourci Bureau n'a pas pu etre cree automatiquement.
    echo Vous pouvez lancer dist\MultiMiner.exe directement, ou creer le
    echo raccourci manuellement ^(clic droit sur l'exe ^> Envoyer vers ^> Bureau^).
)

echo.
echo ============================================
echo   Compilation terminee avec succes.
echo   Executable      : dist\MultiMiner.exe
echo   Mineur CPU      : integre dans dist\miner\
echo   Raccourci Bureau: cree automatiquement
echo   Desinstalleur   : dist\Uninstall.bat
echo ============================================

endlocal
