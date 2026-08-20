# fetch_gpu_miner.ps1
# Telecharge automatiquement lolMiner (mineur GPU open source, AMD +
# NVIDIA, activement maintenu) depuis sa release officielle GitHub, et
# l'extrait dans miner/gpu/.
#
# Depot officiel : https://github.com/Lolliedieb/lolMiner-releases
# Version verifiee manuellement : 1.98a (contient lolMiner.exe, PE32+
# x64 Windows).
#
# Appele automatiquement par l'installateur graphique et par
# scripts\build_advanced.bat. Peut aussi etre execute seul :
#   powershell -ExecutionPolicy Bypass -File scripts\fetch_gpu_miner.ps1

$ErrorActionPreference = "Stop"

$releaseUrl = "https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.98a/lolMiner_v1.98a_Win64.zip"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$minerDir = Join-Path $projectRoot "miner\gpu"
$zipPath = Join-Path $env:TEMP "lolminer-download.zip"
$extractDir = Join-Path $env:TEMP "lolminer-extract"

if (-not (Test-Path $minerDir)) {
    New-Item -ItemType Directory -Path $minerDir -Force | Out-Null
}

Write-Host "[Mineur GPU] Telechargement depuis $releaseUrl ..."
try {
    Invoke-WebRequest -Uri $releaseUrl -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Host "[Mineur GPU] Echec du telechargement : $_"
    exit 1
}

if (Test-Path $extractDir) {
    Remove-Item $extractDir -Recurse -Force
}

Write-Host "[Mineur GPU] Extraction..."
try {
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
} catch {
    Write-Host "[Mineur GPU] Echec de l'extraction : $_"
    exit 1
}

# L'archive contient un sous-dossier versionne (ex: 1.98a\lolMiner.exe)
$exeSource = Get-ChildItem -Path $extractDir -Filter "lolMiner.exe" -Recurse | Select-Object -First 1

if ($null -eq $exeSource) {
    Write-Host "[Mineur GPU] lolMiner.exe introuvable dans l'archive telechargee."
    exit 1
}

Copy-Item $exeSource.FullName (Join-Path $minerDir "lolMiner.exe") -Force
Write-Host "[Mineur GPU] Installe : lolMiner.exe"

Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[Mineur GPU] Installation terminee dans $minerDir"
Write-Host "[Mineur GPU] Algorithme par defaut : AUTOLYKOS2 (Ergo)."
