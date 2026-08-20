@echo off
REM Uninstall.bat
REM Supprime le raccourci Bureau et le dossier d'installation de MultiMiner.
REM Ce fichier est cense se trouver a cote de MultiMiner.exe (dossier dist).

setlocal enabledelayedexpansion

set "APPDIR=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\MultiMiner.lnk"

echo ============================================
echo   Desinstallation de MultiMiner
echo ============================================
echo.
echo Ceci va supprimer :
echo   - le raccourci Bureau
echo   - le dossier d'application : %APPDIR%
echo.
set /p CONFIRM="Continuer ? (O/N) "
if /i not "%CONFIRM%"=="O" (
    echo Desinstallation annulee.
    pause
    goto :eof
)

REM Arret du mineur/de l'app si encore lance
taskkill /f /im MultiMiner.exe >nul 2>nul

if exist "%SHORTCUT%" (
    del /f /q "%SHORTCUT%"
    echo Raccourci Bureau supprime.
)

REM On ne peut pas supprimer ce dossier pendant que ce script s'execute
REM depuis celui-ci : on lance un nettoyeur temporaire qui termine le travail.
set "TMPUNINST=%TEMP%\MultiMiner_uninstall_helper.bat"

echo @echo off > "%TMPUNINST%"
echo timeout /t 2 /nobreak ^>nul >> "%TMPUNINST%"
echo rmdir /s /q "%APPDIR%" >> "%TMPUNINST%"
echo del /f /q "%%~f0" >> "%TMPUNINST%"

echo Suppression du dossier d'application en cours...
start "" /min cmd /c "%TMPUNINST%"

echo.
echo Desinstallation terminee. Cette fenetre peut se fermer.
pause
