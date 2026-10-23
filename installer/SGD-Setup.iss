[Setup]
AppId={{E44F87AE-CE4A-4E30-A3C1-10F9822BFC3B}
AppName=SGD - Gestion Restaurant
AppVersion=1.0.0
DefaultDirName={commonpf}\SGB
DefaultGroupName=SGD - Gestion Restaurant
OutputBaseFilename=SGD-Setup-building
OutputDir=..\release
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
SetupIconFile=..\SGD.ico
WizardStyle=modern
UninstallDisplayIcon={app}\GestionRestaurant.exe
ArchitecturesInstallIn64BitMode=x64
AppendDefaultDirName=no
CreateAppDir=yes
UsePreviousAppDir=no
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=no
DisableReadyMemo=no
DisableReadyPage=no
DisableFinishedPage=no

[Files]
Source: "..\dist\GestionRestaurant.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SGD.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\Data"; Permissions: users-modify

[Icons]
Name: "{commonprograms}\SGD - Gestion Restaurant"; Filename: "{app}\GestionRestaurant.exe"; WorkingDir: "{app}"; IconFilename: "{app}\GestionRestaurant.exe"
Name: "{commondesktop}\SGD - Gestion Restaurant"; Filename: "{app}\GestionRestaurant.exe"; WorkingDir: "{app}"; IconFilename: "{app}\GestionRestaurant.exe"

[Run]
Filename: "{app}\GestionRestaurant.exe"; Description: "Lancer SGD"; Flags: nowait postinstall skipifsilent
