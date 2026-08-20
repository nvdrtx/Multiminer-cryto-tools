# create_shortcut.ps1
# Cree un raccourci "MultiMiner.lnk" sur le Bureau de l'utilisateur,
# pointant vers dist\MultiMiner.exe, avec l'icone du logo.
#
# Appele automatiquement par build.bat a la fin de la compilation.

param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,

    [Parameter(Mandatory = $true)]
    [string]$IconPath
)

if (-not (Test-Path $ExePath)) {
    Write-Host "[Raccourci] Executable introuvable : $ExePath - raccourci non cree."
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "MultiMiner.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $ExePath
$shortcut.WorkingDirectory = Split-Path $ExePath -Parent
$shortcut.Description = "MultiMiner - Interface de minage"

if (Test-Path $IconPath) {
    $shortcut.IconLocation = $IconPath
} else {
    $shortcut.IconLocation = $ExePath
}

$shortcut.Save()

Write-Host "[Raccourci] Cree sur le Bureau : $shortcutPath"
