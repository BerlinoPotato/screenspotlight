; Build with installer/build_installer.py after rebuilding the portable app.
#define AppName "Screen Spotlight"
#define AppExe AddBackslash(SourcePath) + "..\dist\ScreenSpotlight.exe"
#define AppVersion GetStringFileInfo(AppExe, "ProductVersion")
#ifndef ExpectedVersion
  #error Build using installer/build_installer.py to verify the application version.
#endif
#if AppVersion != ExpectedVersion
  #error The executable version does not match spotlight.py. Rebuild the application.
#endif

[Setup]
AppId={{791218E2-B216-4A44-AAD4-75214B8924CC}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
DefaultDirName={localappdata}\Programs\Screen Spotlight
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
WizardStyle=modern
SetupIconFile=..\screenspotlight.ico
UninstallDisplayIcon={app}\ScreenSpotlight.exe
UninstallDisplayName={#AppName}
OutputDir=..\dist
OutputBaseFilename=ScreenSpotlight-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\ScreenSpotlight.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\ScreenSpotlight.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\ScreenSpotlight.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent unchecked
