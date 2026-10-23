#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$projectDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$executable = Join-Path $projectDirectory 'dist\GestionRestaurant.exe'
$buildManifestPath = Join-Path $projectDirectory 'dist\SGD-build-manifest.json'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf) -or
    -not (Test-Path -LiteralPath $buildManifestPath -PathType Leaf)) {
    throw 'Compilez d abord le programme avec ..\build_windows.ps1.'
}
$buildManifest = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
foreach ($relativePath in @('main.py', 'database.py', 'GestionRestaurant.spec', 'SGD.ico', 'SGD.png')) {
    $expectedHash = $buildManifest.source_sha256.$relativePath
    $actualHash = (Get-FileHash -LiteralPath (Join-Path $projectDirectory $relativePath) -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) { throw "La compilation est perimee : $relativePath a change. Recompilez SGD." }
}
if ((Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash -ne $buildManifest.executable_sha256) {
    throw 'L executable compile ne correspond pas au manifeste. Recompilez SGD.'
}

$compilerCandidates = @()
$compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($null -ne $compilerCommand) {
    $compilerCandidates += $compilerCommand.Source
}
foreach ($programFiles in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
    if (-not [string]::IsNullOrWhiteSpace($programFiles)) {
        $compilerCandidates += Join-Path $programFiles 'Inno Setup 6\ISCC.exe'
    }
}
if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $compilerCandidates += Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
}
$compiler = $compilerCandidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($compiler)) {
    throw 'Le compilateur Inno Setup 6 (ISCC.exe) est introuvable. Installez Inno Setup 6 sur le PC de developpement : https://jrsoftware.org/isdl.php'
}

$distributionDirectory = Join-Path $projectDirectory 'release'
$installerDefinition = Join-Path $PSScriptRoot 'SGD-Setup.iss'
$temporarySetupExe = Join-Path $distributionDirectory 'SGD-Setup-building.exe'
$setupExe = Join-Path $distributionDirectory 'SGD-Setup.exe'
New-Item -ItemType Directory -Path $distributionDirectory -Force | Out-Null
if (Test-Path -LiteralPath $temporarySetupExe -PathType Leaf) {
    Remove-Item -LiteralPath $temporarySetupExe -Force
}

Push-Location $projectDirectory
try {
    & $compiler /Qp $installerDefinition
    if ($LASTEXITCODE -ne 0) {
        throw "La compilation Inno Setup a echoue (code $LASTEXITCODE)."
    }
}
finally {
    Pop-Location
}
if (-not (Test-Path -LiteralPath $temporarySetupExe -PathType Leaf) -or
    (Get-Item -LiteralPath $temporarySetupExe).Length -le 0) {
    throw 'Inno Setup n a pas produit un installateur valide.'
}

if (Test-Path -LiteralPath $setupExe -PathType Leaf) {
    $backupSetupExe = Join-Path $distributionDirectory ('SGD-Setup-backup-' + [guid]::NewGuid().ToString('N') + '.exe')
    [IO.File]::Replace($temporarySetupExe, $setupExe, $backupSetupExe)
    try {
        Remove-Item -LiteralPath $backupSetupExe -Force -ErrorAction Stop
    }
    catch {
        Write-Warning "Le nouvel installateur est cree, mais l ancien fichier utilise comme sauvegarde est verrouille : $backupSetupExe"
    }
}
else {
    [IO.File]::Move($temporarySetupExe, $setupExe)
}
Write-Host "Installateur client cree : $setupExe"
Write-Host 'Le paquet ne contient ni base de donnees, ni fichier .env, ni source du projet.'
