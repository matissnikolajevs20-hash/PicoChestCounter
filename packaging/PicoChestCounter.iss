#ifndef AppVersion
  #error AppVersion must be supplied, for example /DAppVersion=1.0.1
#endif

#define AppName "Delta Chest Counter"
#define AppExeName "DeltaChestCounter.exe"

[Setup]
AppId={{A8153AC9-7E42-4B3E-94CB-51EA21E572AB}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=matissnikolajevs20-hash
DefaultDirName={localappdata}\Programs\Delta Chest Counter
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=PicoChestCounter-Setup
SetupIconFile=..\build\delta-chest-counter.ico
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
CloseApplications=no
ArchitecturesInstallIn64BitMode=x64
Compression=lzma2
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\DeltaChestCounter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\app_version.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\update-config.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
