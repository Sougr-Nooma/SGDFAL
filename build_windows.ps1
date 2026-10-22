#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
Set-Location $projectDirectory

$python = Get-Command python -ErrorAction Stop
& $python.Source -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller n''est pas installe pour ce Python. Installez-le avec : python -m pip install pyinstaller'
}

# La specification n'embarque ni restaurant.db, ni .env, ni secret SMTP.
& $python.Source -m PyInstaller --noconfirm --clean GestionRestaurant.spec
if ($LASTEXITCODE -ne 0) { throw 'La compilation PyInstaller a echoue.' }

$executable = Join-Path $projectDirectory 'dist\GestionRestaurant.exe'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "La compilation n'a pas produit $executable"
}
# Marquer l'artefact avec les empreintes des sources de compilation afin que
# l'installateur refuse un ancien .exe, par exemple celui du dossier dist existant.
$sourceFiles = @('main.py', 'database.py', 'GestionRestaurant.spec', 'SGD.ico', 'SGD.png')
$sourceHashes = @{}
foreach ($relativePath in $sourceFiles) {
    $sourcePath = Join-Path $projectDirectory $relativePath
    $sourceHashes[$relativePath] = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
}
$manifest = @{
    source_sha256 = $sourceHashes
    executable_sha256 = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
}
$manifestPath = Join-Path $projectDirectory 'dist\SGD-build-manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "Executable SGD pret pour l'installation : $executable"
Write-Host "Manifeste de compilation : $manifestPath"
Write-Host 'Pour creer l installateur client autonome, lancez installer\build_installer.ps1.'
