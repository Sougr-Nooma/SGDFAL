[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
ExtractTitle=Installation de SGD
InsideCompressed=1
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=SGD est installe dans C:\Program Files\SGB. Lancez-le avec le raccourci du Bureau.
TargetName=release\SGD-Setup-building.exe
FriendlyName=SGD - Gestion Restaurant
AppLaunched=cmd.exe /d /c Launch-SGD-Installer.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[SourceFiles]
SourceFiles0=build\installer-payload
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
%FILE3%=
[Strings]
FILE0="GestionRestaurant.exe"
FILE1="Install-SGD.ps1"
FILE2="SGD-payload-manifest.json"
FILE3="Launch-SGD-Installer.cmd"
