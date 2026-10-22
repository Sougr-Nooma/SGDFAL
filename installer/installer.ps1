#requires -Version 5.1
#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

$interactiveIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
if ($interactiveIdentity.User -eq $null) {
    throw 'Impossible d''identifier le compte Windows qui utilisera SGD.'
}

$installDirectory = Join-Path $env:ProgramFiles 'SGB'
$dataDirectory = Join-Path $installDirectory 'Data'
$executable = Join-Path $installDirectory 'GestionRestaurant.exe'
$publicDesktop = [Environment]::GetFolderPath('CommonDesktopDirectory')
$shortcutPath = Join-Path $publicDesktop 'SGD - Gestion Restaurant.lnk'
if (-not (Test-Path -LiteralPath $publicDesktop -PathType Container)) {
    $shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'SGD - Gestion Restaurant.lnk'
}

$projectDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$sourceExecutable = Join-Path $projectDirectory 'dist\GestionRestaurant.exe'
$manifestPath = Join-Path $projectDirectory 'dist\SGD-build-manifest.json'
if (-not (Test-Path -LiteralPath $sourceExecutable -PathType Leaf)) {
    throw "Exécutable introuvable : $sourceExecutable. Lancez d'abord build_windows.ps1."
}
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Manifeste de compilation manquant. Compilez le projet avec build_windows.ps1 avant l'installation."
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
foreach ($relativePath in @('main.py', 'database.py', 'GestionRestaurant.spec', 'SGD.ico', 'SGD.png')) {
    $sourcePath = Join-Path $projectDirectory $relativePath
    $actualHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    $expectedHash = $manifest.source_sha256.$relativePath
    if ($actualHash -ne $expectedHash) {
        throw "La compilation est ancienne (source modifiee depuis la compilation : $relativePath). Relancez build_windows.ps1."
    }
}
if ((Get-FileHash -LiteralPath $sourceExecutable -Algorithm SHA256).Hash -ne $manifest.executable_sha256) {
    throw 'L''executable a ete modifie depuis la compilation. Relancez build_windows.ps1.'
}

New-Item -ItemType Directory -Path $installDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
Copy-Item -LiteralPath $sourceExecutable -Destination $executable -Force

# La base reste locale, dans Program Files\SGB\Data. Seul le dossier de données
# est modifiable par l'utilisateur courant; les binaires installés restent protégés.
$userIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $dataDirectory '/inheritance:r' '/grant:r' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "${userIdentity}:(OI)(CI)M" | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Impossible de définir les droits du dossier Data.' }

# Identifiants SMTP saisis sur le poste, jamais dans le code ou le binaire.
$gmailAddress = Read-Host 'Adresse Gmail expéditrice (laisser vide pour configurer Gmail plus tard)'
$gmailAppPassword = ''
if (-not [string]::IsNullOrWhiteSpace($gmailAddress)) {
    if ($gmailAddress -notmatch '^[^\s@]+@gmail\.com$') {
        throw 'Saisissez une adresse @gmail.com valide, ou laissez le champ vide.'
    }
    $securePassword = Read-Host 'Mot de passe d''application Google (pas votre mot de passe Gmail)' -AsSecureString
    $passwordPointer = [IntPtr]::Zero
    try {
        $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        $gmailAppPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer) -replace '\s', ''
    }
    finally {
        if ($passwordPointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
        }
        $securePassword.Dispose()
    }
    if ([string]::IsNullOrWhiteSpace($gmailAppPassword)) {
        throw 'Le mot de passe d’application ne peut pas être vide.'
    }
}

$configDirectory = Join-Path $env:APPDATA 'SGD'
New-Item -ItemType Directory -Path $configDirectory -Force | Out-Null
$configPath = Join-Path $configDirectory '.env'
$encryptedAppPassword = ''
if (-not [string]::IsNullOrWhiteSpace($gmailAppPassword)) {
    Add-Type -AssemblyName System.Security
    $passwordBytes = [Text.Encoding]::UTF8.GetBytes($gmailAppPassword)
    $protectedBytes = [Security.Cryptography.ProtectedData]::Protect(
        $passwordBytes,
        $null,
        [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    $encryptedAppPassword = [Convert]::ToBase64String($protectedBytes)
    [Array]::Clear($passwordBytes, 0, $passwordBytes.Length)
    $gmailAppPassword = $null
}

$configLines = @(
    '# Configuration SMTP privee a cet utilisateur Windows; ne pas partager ce fichier.',
    '# Le mot de passe d application Gmail est chiffre par DPAPI pour ce compte Windows.',
    'SGD_SMTP_HOST=smtp.gmail.com',
    'SGD_SMTP_PORT=587',
    "SGD_SMTP_USER=$gmailAddress",
    "SGD_SMTP_PASSWORD_DPAPI=$encryptedAppPassword",
    "SGD_SMTP_FROM=$gmailAddress"
)
if ([string]::IsNullOrWhiteSpace($gmailAddress) -and (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    Write-Host 'Adresse Gmail vide : la configuration Gmail existante est conservee.'
}
else {
    [IO.File]::WriteAllLines($configPath, $configLines, [Text.UTF8Encoding]::new($false))
    & icacls.exe $configPath '/inheritance:r' '/grant:r' '*S-1-5-18:F' '*S-1-5-32-544:F' "${userIdentity}:F" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Impossible de protéger le fichier de configuration Gmail.' }
}
$gmailAppPassword = $null
$encryptedAppPassword = $null

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $executable
$shortcut.WorkingDirectory = $installDirectory
$shortcut.IconLocation = "$executable,0"
$shortcut.Description = 'SGD - Gestion Restaurant'
$shortcut.Save()

Write-Host ''
Write-Host "Installation terminee : $executable"
Write-Host "Base locale (creee au premier lancement) : $dataDirectory\restaurant.db"
Write-Host "Configuration Gmail privee (mot de passe chiffre par DPAPI) : $configPath"
Write-Host "Raccourci Bureau : $shortcutPath"
if ([string]::IsNullOrWhiteSpace($gmailAddress)) {
    Write-Host 'SMTP non configure. Relancez ce script avec une adresse Gmail et son mot de passe d application pour activer la recuperation par courriel.'
}
Write-Host 'Au premier demarrage, creez le premier compte dans SGD.'
