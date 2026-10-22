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

$iexpress = Join-Path $env:WINDIR 'System32\iexpress.exe'
if (-not (Test-Path -LiteralPath $iexpress -PathType Leaf)) { throw 'IExpress de Windows est introuvable.' }
$stagingDirectory = Join-Path $projectDirectory 'build\installer-payload'
$distributionDirectory = Join-Path $projectDirectory 'release'
New-Item -ItemType Directory -Path $stagingDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $distributionDirectory -Force | Out-Null
$payloadExe = Join-Path $stagingDirectory 'GestionRestaurant.exe'
$payloadScript = Join-Path $stagingDirectory 'Install-SGD.ps1'
$payloadLauncher = Join-Path $stagingDirectory 'Launch-SGD-Installer.cmd'
Copy-Item -LiteralPath $executable -Destination $payloadExe -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install_payload.ps1') -Destination $payloadScript -Force
$launcherLines = @(
    '@echo off',
    'setlocal',
    'cd /d "%~dp0"',
    'echo Demarrage de l installation SGD...',
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-SGD.ps1"',
    'set "installExitCode=%ERRORLEVEL%"',
    'if not "%installExitCode%"=="0" (',
    '    echo.',
    '    echo L installation a echoue avec le code %installExitCode%.',
    '    echo Lisez le message ci-dessus, puis contactez le support.',
    '    pause',
    '    exit /b %installExitCode%',
    ')',
    'exit /b 0'
)
[IO.File]::WriteAllLines($payloadLauncher, $launcherLines, [Text.Encoding]::ASCII)
$payloadManifest = @{ executable_sha256 = (Get-FileHash -LiteralPath $payloadExe -Algorithm SHA256).Hash }
$payloadManifestPath = Join-Path $stagingDirectory 'SGD-payload-manifest.json'
$payloadManifest | ConvertTo-Json | Set-Content -LiteralPath $payloadManifestPath -Encoding UTF8

# Génère le fichier de définition SED d'IExpress pour un installateur auto-extractible.
$sedPath = Join-Path $projectDirectory 'build\SGD-Setup.sed'
$setupExe = Join-Path $distributionDirectory 'SGD-Setup.exe'
$temporarySetupExe = Join-Path $distributionDirectory 'SGD-Setup-building.exe'
$sedLines = @(
    '[Version]',
    'Class=IEXPRESS',
    'SEDVersion=3',
    '[Options]',
    'PackagePurpose=InstallApp',
    'ShowInstallProgramWindow=1',
    'HideExtractAnimation=1',
    'UseLongFileName=1',
    'ExtractTitle=Installation de SGD',
    'InsideCompressed=1',
    'CAB_FixedSize=0',
    'CAB_ResvCodeSigning=0',
    'RebootMode=N',
    'InstallPrompt=',
    'DisplayLicense=',
    'FinishMessage=SGD est installe dans C:\Program Files\SGB. Lancez-le avec le raccourci du Bureau.',
    'TargetName=release\SGD-Setup-building.exe',
    'FriendlyName=SGD - Gestion Restaurant',
    'AppLaunched=cmd.exe /d /c Launch-SGD-Installer.cmd',
    'PostInstallCmd=<None>',
    'AdminQuietInstCmd=',
    'UserQuietInstCmd=',
    'SourceFiles=SourceFiles',
    '[SourceFiles]',
    'SourceFiles0=build\installer-payload',
    '[SourceFiles0]',
    '%FILE0%=',
    '%FILE1%=',
    '%FILE2%=',
    '%FILE3%=',
    '[Strings]',
    'FILE0="GestionRestaurant.exe"',
    'FILE1="Install-SGD.ps1"',
    'FILE2="SGD-payload-manifest.json"',
    'FILE3="Launch-SGD-Installer.cmd"'
)
[IO.File]::WriteAllLines($sedPath, $sedLines, [Text.Encoding]::Default)
if (Test-Path -LiteralPath $temporarySetupExe -PathType Leaf) {
    Remove-Item -LiteralPath $temporarySetupExe -Force
}
$iexpressProcess = Start-Process -FilePath $iexpress -ArgumentList @('/N', '/Q', 'build\SGD-Setup.sed') `
    -WorkingDirectory $projectDirectory -PassThru
$buildDeadline = [DateTime]::Now.AddMinutes(10)
$lastPackageLength = -1
$stablePackageChecks = 0
while ([DateTime]::Now -lt $buildDeadline) {
    if (Test-Path -LiteralPath $temporarySetupExe -PathType Leaf) {
        $packageLength = (Get-Item -LiteralPath $temporarySetupExe).Length
        if ($packageLength -gt 0 -and $packageLength -eq $lastPackageLength) {
            $stablePackageChecks++
            if ($stablePackageChecks -ge 2) { break }
        }
        else {
            $stablePackageChecks = 0
        }
        $lastPackageLength = $packageLength
    }
    else {
        $lastPackageLength = -1
        $stablePackageChecks = 0
    }
    Start-Sleep -Seconds 5
}
if (-not (Test-Path -LiteralPath $temporarySetupExe -PathType Leaf)) {
    if (-not $iexpressProcess.HasExited) {
        Stop-Process -Id $iexpressProcess.Id -ErrorAction SilentlyContinue
    }
    throw "IExpress n a pas produit l installateur apres 10 minutes. Verifiez $sedPath."
}
if ((Get-Item -LiteralPath $temporarySetupExe).Length -le 0) {
    Remove-Item -LiteralPath $temporarySetupExe -Force
    throw 'IExpress a produit un fichier installateur vide.'
}
Copy-Item -LiteralPath $temporarySetupExe -Destination $setupExe -Force
Remove-Item -LiteralPath $temporarySetupExe -Force
Write-Host "Installateur client cree : $setupExe"
Write-Host 'Il installe uniquement le programme : aucune base de developpement ou configuration .env n est incluse.'
