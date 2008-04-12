; Directions for use
; ==================
; 1. Download BPBible from SVN (or whereever). Run "python setup.py py2exe".
;    This will compile BPBible for Windows.
; 2. Copy gdiplus.dll from the wxWidgets folder (e.g. wx-2.8-msw-unicode\wx\
;    gdiplus.dll) to this folder (installer\gdiplus.dll)
; 3. Update the version number (from 0.2).  Change AppVerName, AppVersion,
;    VersionInfoTextVersion, VersionInfoVersion and OutputBaseFilename.
;    In Vim, you can just do :%s/0.2/{new version}/g
;    NOTE: if you add another number (e.g. 0.2.1) you will need to update
;          the VersionInfoVersion line manually
; 4. You may need to update any paths that have changed for the
;    [UninstallFiles] section - an official change may be being made for
;    the location of *.idx files and per-user setting may become (semi)
;    standard. (%APPDATA% is {userappdata})
; 5. Run InnoSetup and compile this file!

[Setup]
AppName=BPBible
AppVerName=BPBible 0.2
AppPublisher=Benjamin Morgan
AppPublisherURL=http://BPBible.GoogleCode.com/
AppSupportURL=http://BPBible.GoogleCode.com/
AppUpdatesURL=http://BPBible.GoogleCode.com/
AppReadmeFile={app}\README.txt
AppCopyright=© 2008 Benjamin Morgan
AppId=BPBible
AppVersion=0.2
VersionInfoCompany=BPBible
VersionInfoCopyright=© 2008 Benjamin Morgan
VersionInfoDescription=BPBible is a flexible Bible Study tool...
VersionInfoTextVersion=0.2
VersionInfoVersion=0.2.0.0
DefaultDirName={pf}\BPBible
DefaultGroupName=BPBible
AllowNoIcons=yes
InfoBeforeFile=Info.rtf
OutputDir=.
OutputBaseFilename=bpbible-0.2-setup
SetupIconFile=..\graphics\bpbible.ico
SolidCompression=yes
Compression=lzma/ultra
InternalCompressLevel=ultra
WizardImageFile=installer-side.bmp
WizardSmallImageFile=installer-small.bmp

Uninstallable=yes
UninstallDisplayIcon={app}\bpbible.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "uninstall.ico"; DestDir: "{app}"; Flags: ignoreversion
; Shared library needed for Windows 2000 and down. Redistributable, so it's legal.
Source: "gdiplus.dll"; DestDir: "{app}"; OnlyBelowVersion: 5.0,5.01

[Dirs]
Name: "{app}\resources"
Name: "{app}\data"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var SWORDPath: String;
begin
	if CurStep=ssPostInstall then begin
		// Detect The SWORD Project for Windows and set the resources path to include it.
		if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\sword.exe', 'Path', SWORDPath) then begin
			SetIniString('Install', 'DataPath', SWORDPath, ExpandConstant('{app}\sword.conf'));
			SetIniString('Install', 'AugmentPath', ExpandConstant('{app}\resources'), ExpandConstant('{app}\sword.conf'));
			MsgBox('The SWORD Project was found in ' + SWORDPath + '.'+#10+'If you extract your modules to there (or use the SWORD Project install manager), then you can use them in BPBible as well as The SWORD Project.' + #10 + 'To make modules functional for BPBible only, extract them to ' + ExpandConstant('{app}\resources') + '.', mbInformation, MB_OK);
		end else begin
			SetIniString('Install', 'DataPath', ExpandConstant('{app}\resources'), ExpandConstant('{app}\sword.conf'));
			MsgBox('The SWORD Project was not found on your computer.'+#10+#10+'The easiest place to extract your modules to is ' + ExpandConstant('{app}\resources'), mbInformation, MB_OK);
		end;
	end;
end;
[EndCode]

[Icons]
Name: "{group}\BPBible"; Filename: "{app}\bpbible.exe"; Comment: "Run BPBible - read the Bible!"
Name: "{group}\{cm:UninstallProgram,BPBible}"; Filename: "{uninstallexe}"; IconFilename: "{app}\uninstall.ico"; Comment: "Uninstall BPBible"
Name: "{userdesktop}\BPBible"; Filename: "{app}\bpbible.exe"; Tasks: desktopicon; Comment: "Run BPBible - read the Bible!"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\BPBible"; Filename: "{app}\bpbible.exe"; Tasks: quicklaunchicon; Comment: "Run BPBible - read the Bible!"

[Run]
Filename: "{app}\bpbible.exe"; Description: "{cm:LaunchProgram,BPBible}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
;Error log
Type: files; Name: "{app}\bpbible.exe.log"
;Paths file
Type: files; Name: "{app}\paths.ini"
;SWORD modules path configuration file
Type: files; Name: "{app}\sword.conf"
;BPBible data
Type: files; Name: "{app}\data\data.conf"
;Search indexes
Type: files; Name: "{app}\*.idx"
