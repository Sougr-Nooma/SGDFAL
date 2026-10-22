#requires -Version 5.1
$ErrorActionPreference = 'Stop'

$payloadDirectory = $PSScriptRoot
$executableSource = Join-Path $payloadDirectory 'GestionRestaurant.exe'
$manifestPath = Join-Path $payloadDirectory 'SGD-payload-manifest.json'
if (-not (Test-Path -LiteralPath $executableSource -PathType Leaf) -or
    -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'Paquet SGD incomplet : executable ou manifeste manquant.'
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $executableSource -Algorithm SHA256).Hash -ne $manifest.executable_sha256) {
    throw 'Verification du paquet SGD impossible : executable altere ou endommage.'
}

# Configure SMTP sous le compte qui lance Setup afin que DPAPI chiffre le secret
# pour le bon profil Windows, avant de demander l elevation administrateur.
$gmailAddress = Read-Host 'Adresse Gmail expediteur (laisser vide pour configurer plus tard)'
if (-not [string]::IsNullOrWhiteSpace($gmailAddress)) {
    if ($gmailAddress -notmatch '^[^\s@]+@gmail\.com$') { throw 'Saisissez une adresse @gmail.com valide.' }
    $securePassword = Read-Host 'Mot de passe d application Google (pas le mot de passe Gmail)' -AsSecureString
    $passwordPointer = [IntPtr]::Zero
    try {
        $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        $gmailAppPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer) -replace '\s', ''
    }
    finally {
        if ($passwordPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer) }
        $securePassword.Dispose()
    }
    if ([string]::IsNullOrWhiteSpace($gmailAppPassword)) { throw 'Le mot de passe d application ne peut pas etre vide.' }

    Add-Type -AssemblyName System.Security
    $passwordBytes = [Text.Encoding]::UTF8.GetBytes($gmailAppPassword)
    try {
        $protectedBytes = [Security.Cryptography.ProtectedData]::Protect(
            $passwordBytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        $encryptedAppPassword = [Convert]::ToBase64String($protectedBytes)
    }
    finally { [Array]::Clear($passwordBytes, 0, $passwordBytes.Length) }
    $configDirectory = Join-Path $env:APPDATA 'SGD'
    New-Item -ItemType Directory -Path $configDirectory -Force | Out-Null
    $configPath = Join-Path $configDirectory '.env'
    $configLines = @(
        '# Configuration SMTP privee; mot de passe protege par DPAPI pour ce profil Windows.',
        'SGD_SMTP_HOST=smtp.gmail.com',
        'SGD_SMTP_PORT=587',
        "SGD_SMTP_USER=$gmailAddress",
        "SGD_SMTP_PASSWORD_DPAPI=$encryptedAppPassword",
        "SGD_SMTP_FROM=$gmailAddress"
    )
    [IO.File]::WriteAllLines($configPath, $configLines, [Text.UTF8Encoding]::new($false))
    $configUserSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $configPath '/inheritance:r' '/grant:r' '*S-1-5-18:F' '*S-1-5-32-544:F' "*${configUserSid}:F" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Impossible de proteger la configuration Gmail.' }
    $gmailAppPassword = $null
    $protectedBytes = $null
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $scriptPath = $PSCommandPath.Replace("'", "''")
    $installUserSid = $identity.User.Value
    $command = "`$env:SGD_INSTALL_USER_SID='$installUserSid'; & '$scriptPath'"
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $powershell = Join-Path $PSHOME 'powershell.exe'
    $process = Start-Process -FilePath $powershell -Verb RunAs -Wait -PassThru -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $encodedCommand
    )
    if ($process.ExitCode -ne 0) { throw "L'installation SGD a echoue (code $($process.ExitCode))." }
    exit 0
}

$installDirectory = Join-Path $env:ProgramFiles 'SGB'
$dataDirectory = Join-Path $installDirectory 'Data'
$executable = Join-Path $installDirectory 'GestionRestaurant.exe'
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
Copy-Item -LiteralPath $executableSource -Destination $executable -Force
$userSid = $env:SGD_INSTALL_USER_SID
if ([string]::IsNullOrWhiteSpace($userSid)) { $userSid = $identity.User.Value }
& icacls.exe $dataDirectory '/inheritance:r' '/grant:r' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "*${userSid}:(OI)(CI)M" | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Impossible de definir les droits du dossier Data.' }

$desktop = [Environment]::GetFolderPath('CommonDesktopDirectory')
if (-not (Test-Path -LiteralPath $desktop -PathType Container)) {
    $desktop = [Environment]::GetFolderPath('Desktop')
}
$shortcutPath = Join-Path $desktop 'SGD - Gestion Restaurant.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $executable
$shortcut.WorkingDirectory = $installDirectory
$shortcut.IconLocation = "$executable,0"
$shortcut.Description = 'SGD - Gestion Restaurant'
$shortcut.Save()

Write-Host ''
Write-Host "SGD est installe dans : $installDirectory"
Write-Host "La base sera creee au premier lancement dans : $dataDirectory\restaurant.db"
Write-Host "Raccourci cree : $shortcutPath"
Write-Host 'Lancez SGD avec le raccourci puis creez le premier compte.'
