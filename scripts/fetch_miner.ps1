# fetch_miner.ps1
# Telecharge automatiquement cpuminer-multi (mineur CPU open source,
# protocole Stratum) depuis sa release officielle sur GitHub, et
# l'extrait dans le dossier miner/.
#
# Depot officiel : https://github.com/tpruvot/cpuminer-multi
# Cette release est verifiee manuellement : elle contient 3 binaires
# Windows x64 (core2 / corei7 / avx2) optimises pour differents CPU.
#
# Appele automatiquement par build.bat. Peut aussi etre execute seul :
#   powershell -ExecutionPolicy Bypass -File scripts\fetch_miner.ps1

$ErrorActionPreference = "Stop"

$releaseUrl = "https://github.com/tpruvot/cpuminer-multi/releases/download/v1.3.1-multi/cpuminer-multi-rel1.3.1-x64.zip"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$minerDir = Join-Path $projectRoot "miner"
$zipPath = Join-Path $env:TEMP "cpuminer-multi-download.zip"
$extractDir = Join-Path $env:TEMP "cpuminer-multi-extract"

if (-not (Test-Path $minerDir)) {
    New-Item -ItemType Directory -Path $minerDir | Out-Null
}

Write-Host "[Mineur] Telechargement depuis $releaseUrl ..."
try {
    Invoke-WebRequest -Uri $releaseUrl -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Host "[Mineur] Echec du telechargement : $_"
    exit 1
}

if (Test-Path $extractDir) {
    Remove-Item $extractDir -Recurse -Force
}

Write-Host "[Mineur] Extraction..."
try {
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
} catch {
    Write-Host "[Mineur] Echec de l'extraction : $_"
    exit 1
}

$binaries = @(
    "cpuminer-gw64-core2.exe",
    "cpuminer-gw64-corei7.exe",
    "cpuminer-gw64-avx2.exe"
)

foreach ($bin in $binaries) {
    $src = Join-Path $extractDir $bin
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $minerDir $bin) -Force
        Write-Host "[Mineur] Installe : $bin"
    }
}

Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[Mineur] Installation terminee dans $minerDir"
Write-Host "[Mineur] Par defaut, MultiMiner utilisera cpuminer-gw64-corei7.exe."
Write-Host "[Mineur] Si votre CPU est ancien et que le mineur plante, choisissez"
Write-Host "[Mineur] cpuminer-gw64-core2.exe dans Parametres a la place."
