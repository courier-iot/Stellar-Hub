; Stellar Hub Windows installer. GitHub Actions builds this with Inno Setup on every release:
; it bundles its own Python, so nothing else needs installing first.
; Installs per user (no admin needed) into %LOCALAPPDATA%\StellarHub.
; Updating keeps config.json and the resident's mind (the data folder). Uninstalling keeps them too.

#define MyAppName "Stellar Hub"
#define MyAppVersion GetEnv("APP_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{6E1B2C9A-4F7D-4B8E-9A3C-2D5F7E1A9B40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Stellar Hub
DefaultDirName={localappdata}\StellarHub
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir=..\out
OutputBaseFilename=StellarHub-Setup-v{#MyAppVersion}
SetupIconFile=stellarhub.ico
UninstallDisplayIcon={app}\stellarhub.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
MinVersion=10.0

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\build\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
; config.json is never installed: Stellar Hub creates it from config.default.json on first start,
; so updates can't overwrite your settings.
Source: "..\desktop\*"; DestDir: "{app}"; Excludes: "*.sh,config.json,\data\*,__pycache__,*.pyc"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Stellar Hub"; Filename: "{app}\python\python.exe"; Parameters: """{app}\run.py"" --open"; WorkingDir: "{app}"; IconFilename: "{app}\stellarhub.ico"; Comment: "Start the colony. Closing its window stops it."
Name: "{group}\Setup and model check"; Filename: "{app}\python\python.exe"; Parameters: """{app}\setup_hub.py"" --pause"; WorkingDir: "{app}"; IconFilename: "{app}\stellarhub.ico"; Comment: "Check hardware and drivers, choose an AI model"
Name: "{group}\Stop Stellar Hub"; Filename: "{app}\python\python.exe"; Parameters: """{app}\stop.py"" --pause"; WorkingDir: "{app}"; IconFilename: "{app}\stellarhub.ico"
Name: "{group}\Uninstall Stellar Hub"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Stellar Hub"; Filename: "{app}\python\python.exe"; Parameters: """{app}\run.py"" --open"; WorkingDir: "{app}"; IconFilename: "{app}\stellarhub.ico"; Tasks: desktopicon

[INI]
Filename: "{group}\Stellar Hub dashboard.url"; Section: "InternetShortcut"; Key: "URL"; String: "http://localhost:8080"

[Run]
Filename: "{app}\python\python.exe"; Parameters: """{app}\setup_hub.py"" --pause"; WorkingDir: "{app}"; Description: "Check my hardware and choose an AI model (recommended)"; Flags: postinstall skipifsilent
Filename: "{app}\python\python.exe"; Parameters: """{app}\run.py"" --open"; WorkingDir: "{app}"; Description: "Start Stellar Hub now"; Flags: postinstall skipifsilent nowait unchecked
; After a quiet update started from the dashboard, start Stellar Hub again in the background.
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\run.py"""; WorkingDir: "{app}"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "{app}\python\python.exe"; Parameters: """{app}\stop.py"""; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; RunOnceId: "StopHub"

[UninstallDelete]
Type: files; Name: "{userstartup}\Stellar Hub.vbs"
Type: files; Name: "{group}\Stellar Hub dashboard.url"
Type: filesandordirs; Name: "{app}\town\__pycache__"
Type: filesandordirs; Name: "{app}\__pycache__"
