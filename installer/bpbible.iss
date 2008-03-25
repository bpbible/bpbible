; Directions for use
; ==================
; 1. Download BPBible SVN (or whatever).
;    This should be in /installer, and the py2exe output should be in /dist
; 2. Update the "AppVerName" and "OutputBaseFilename" line if necessary for a release.
; 3. Update any paths that have changed for the [UninstallFiles] section - hopefully
;    directory structure will be being cleaned up so that *.idx files aren't put in
;    the root.  Also, hopefully the option of per-user settings will be built in,
;    meaning that we would also need to delete some "{userappdata}\bpbible"... files.

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
DefaultDirName={pf}\BPBible
DefaultGroupName=BPBible
AllowNoIcons=yes
LicenseFile=..\dist\LICENSE.txt
InfoBeforeFile=Info.rtf
OutputDir=.
OutputBaseFilename=bpbible-0.2-setup
SetupIconFile=bpbible.ico
SolidCompression=yes
Compression=lzma/ultra
InternalCompressLevel=ultra
WizardImageFile=installer-side.bmp
WizardSmallImageFile=installer-small.bmp

Uninstallable=yes
UninstallDisplayIcon={app}\bpbible.exe

[Languages]
;Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "english"; MessagesFile: "bpbible-english.isl"
;Removes notes about "important" information - the readme and GPL aren't "important"!

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "uninstall.ico"; DestDir: "{app}"; Flags: ignoreversion
;Source: "gdiplus.dll"; DestDir: "{app}"; Flags: dontcopy
Source: "gdiplus.dll"; DestDir: "{app}"; OnlyBelowVersion: 5.0,5.01

[Dirs]
Name: "{app}\resources"
Name: "{app}\data"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var SWORDPath: String;
begin
    if CurStep=ssPostInstall then begin
        // Win2K does not include GDI+, needed by BPBible.
        // Put it in {app} if they're using Win2K.
//        if GetWindowsVersion<=$05000893 then begin
//            MsgBox('You''re using Windows 200 or less.  GDI+ is not included, so I am about to install it...', mbInformation, MB_OK);
//            ExtractTemporaryFile('gdiplus.dll');
//            MsgBox('gdiplus.dll has been installed.', mbInformation, MB_OK);
//        end;

        // Detect The SWORD Project for Windows and set the resources path to it.
        if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\sword.exe', 'Path', SWORDPath) then begin
            SetIniString('Install', 'DataPath', SWORDPath, ExpandConstant('{app}\sword.conf'));
            SetIniString('Install', 'AugmentPath', ExpandConstant('{app}\resources'), ExpandConstant('{app}\sword.conf'));
            MsgBox('The SWORD Project was found in ' + SWORDPath + '.'+#10+'If you extract your modules to there, then you can use them in BPBible as well as The SWORD Project.' + #10 + 'To make modules functional for BPBible only, extract them to ' + ExpandConstant('{app}\resources') + '.', mbInformation, MB_OK);
        end else begin
            SetIniString('Install', 'AugmentPath', ExpandConstant('{app}\resources'), ExpandConstant('{app}\sword.conf'));
            MsgBox('The SWORD Project was not found on your computer.'+#10+'The easiest place to extract your modules to is ' + ExpandConstant('{app}\resources'), mbInformation, MB_OK);
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
;If it has problems, it logs them here.
Type: files; Name: "{app}\bpbible.exe.log"
;SWORD modules path configuration file
Type: files; Name: "{app}\sword.conf"
;GUI layout details
Type: files; Name: "{app}\data\gui.conf"
;Other data stored
Type: files; Name: "{app}\data\data.conf"
;Delete search indexes created by BPBible
Type: files; Name: "{app}\*.idx"
