;Copyright (C) 2004-2009 John T. Haller of PortableApps.com
;Copyright (C) 2008-2009 Chris Morgan of PortableApps.com

;Website: http://PortableApps.com/BPBiblePortable

;This software is OSI Certified Open Source Software.
;OSI Certified is a certification mark of the Open Source Initiative.

;This program is free software; you can redistribute it and/or
;modify it under the terms of the GNU General Public License
;as published by the Free Software Foundation; either version 2
;of the License, or (at your option) any later version.

;This program is distributed in the hope that it will be useful,
;but WITHOUT ANY WARRANTY; without even the implied warranty of
;MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;GNU General Public License for more details.

;You should have received a copy of the GNU General Public License
;along with this program; if not, write to the Free Software
;Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

!define PORTABLEAPPNAME "BPBible Portable"
!define APPNAME "BPBible"
!define NAME "BPBiblePortable"
!define VER "1.6.1.0"
!define WEBSITE "PortableApps.com/BPBiblePortable"
!define DEFAULTEXE "bpbible.exe"
!define DEFAULTAPPDIR "bpbible"
!define LAUNCHERLANGUAGE "English"

;=== Program Details
Name "${PORTABLEAPPNAME}"
OutFile "..\..\${NAME}.exe"
Caption "${PORTABLEAPPNAME} | PortableApps.com"
VIProductVersion "${VER}"
VIAddVersionKey ProductName "${PORTABLEAPPNAME}"
VIAddVersionKey Comments "Allows ${APPNAME} to be run from a removable drive.  For additional details, visit ${WEBSITE}"
VIAddVersionKey CompanyName "PortableApps.com"
VIAddVersionKey LegalCopyright "PortableApps.com & Contributors"
VIAddVersionKey FileDescription "${PORTABLEAPPNAME}"
VIAddVersionKey FileVersion "${VER}"
VIAddVersionKey ProductVersion "${VER}"
VIAddVersionKey InternalName "${PORTABLEAPPNAME}"
VIAddVersionKey LegalTrademarks "PortableApps.com is a Trademark of Rare Ideas, LLC."
VIAddVersionKey OriginalFilename "${NAME}.exe"
;VIAddVersionKey PrivateBuild ""
;VIAddVersionKey SpecialBuild ""

;=== Runtime Switches
CRCCheck On
WindowIcon Off
SilentInstall Silent
AutoCloseWindow True
RequestExecutionLevel user

; Best Compression
SetCompress Auto
SetCompressor /SOLID lzma
SetCompressorDictSize 32
SetDatablockOptimize On

;=== Include
;(Standard NSIS)
!include FileFunc.nsh
!insertmacro GetParameters
!insertmacro GetParent
!insertmacro GetRoot

;(NSIS Plugins)
!include TextReplace.nsh

;(Custom)
!include ReadINIStrWithDefault.nsh
!include ReplaceInFileWithTextReplace.nsh

;=== Program Icon
Icon "..\..\App\AppInfo\appicon.ico"

;=== Languages
LoadLanguageFile "${NSISDIR}\Contrib\Language files\${LAUNCHERLANGUAGE}.nlf"
!include PortableApps.comLauncherLANG_${LAUNCHERLANGUAGE}.nsh

;=== Variables
!define PROGRAMDIRECTORY "$EXEDIR\App\${DEFAULTAPPDIR}"
!define SETTINGSDIRECTORY "$EXEDIR\Data\settings"
!define RESOURCESDIRECTORY "$EXEDIR\Data\resources"
Var SPPRESOURCESDIRECTORY ; SWORD Project Portable Resources Directory
Var SBPRESOURCESDIRECTORY ; SwordBible Portable Resources Directory
Var USELOCALSPRESOURCES ; Do we use the local SWORD Project Resources if they exist?
Var LOCALSPRESOURCESDIRECTORY ; Local SWORD Project Resources Directory
Var ADDITIONALPARAMETERS
Var EXECSTRING
Var DISABLESPLASHSCREEN
Var LASTRESOURCESDIRECTORY
Var LASTSPPRESOURCESDIRECTORY
Var LASTSBPRESOURCESDIRECTORY
Var LASTLOCALSPRESOURCESDIRECTORY
Var MISSINGFILEORPATH
Var BPBIBLELANGUAGE
Var LASTBPBIBLELANGUAGE
Var LASTDRIVE
Var CURRENTDRIVE

Section "Main"
	;=== Set up the path variables
	${GetParent} $EXEDIR $0
	StrCpy $SPPRESOURCESDIRECTORY "$0\SWORDProjectPortable\Data\settings"
	StrCpy $SBPRESOURCESDIRECTORY "$0\SwordBiblePortable\Data"

	IfFileExists "${PROGRAMDIRECTORY}\${DEFAULTEXE}" CheckINI

	;=== Program executable not where expected
	StrCpy $MISSINGFILEORPATH ${DEFAULTEXE}
	MessageBox MB_OK|MB_ICONEXCLAMATION `$(LauncherFileNotFound)`
	Abort

	CheckINI:
		;=== Find the INI file, if there is one
		IfFileExists "$EXEDIR\${NAME}.ini" "" NoINI

		;=== Read the parameters from the INI file
		${ReadINIStrWithDefault} $ADDITIONALPARAMETERS "$EXEDIR\${NAME}.ini" "${NAME}" "AdditionalParameters" ""
		${ReadINIStrWithDefault} $DISABLESPLASHSCREEN "$EXEDIR\${NAME}.ini" "${NAME}" "DisableSplashScreen" "false"
		${ReadINIStrWithDefault} $USELOCALSPRESOURCES "$EXEDIR\${NAME}.ini" "${NAME}" "UseLocalResources" "false"
		Goto DisplaySplash

	NoINI:
		;=== No INI file, so we'll use the defaults
		StrCpy $ADDITIONALPARAMETERS ""
		StrCpy $DISABLESPLASHSCREEN "false"
		StrCpy $USELOCALSPRESOURCES "false"

	DisplaySplash:
		StrCmp $DISABLESPLASHSCREEN "true" GetPassedParameters
			;=== Show the splash screen while processing data
			InitPluginsDir
			File /oname=$PLUGINSDIR\splash.jpg "${NAME}.jpg"
			newadvsplash::show /NOUNLOAD 2000 0 0 -1 /L $PLUGINSDIR\splash.jpg

	GetPassedParameters:
		;=== Get any passed parameters
		${GetParameters} $0
		StrCmp "'$0'" "''" "" LaunchProgramParameters

		;=== No parameters
		StrCpy $EXECSTRING `"${PROGRAMDIRECTORY}\${DEFAULTEXE}" --data-path="${SETTINGSDIRECTORY}" --index-path="${RESOURCESDIRECTORY}" --sword-path="${SETTINGSDIRECTORY}"`
		Goto AdditionalParameters

	LaunchProgramParameters:
		StrCpy $EXECSTRING `"${PROGRAMDIRECTORY}\${DEFAULTEXE}" --data-path="${SETTINGSDIRECTORY}" --index-path="${RESOURCESDIRECTORY}" --sword-path="${SETTINGSDIRECTORY}" $0`

	AdditionalParameters:
		StrCmp $ADDITIONALPARAMETERS "" BPBibleLanguageGLIBC

		;=== Additional Parameters
		StrCpy $EXECSTRING `$EXECSTRING $ADDITIONALPARAMETERS`

	BPBibleLanguageGLIBC:
		; e.g. en_US, hu
		ReadEnvStr $BPBIBLELANGUAGE "PortableApps.comLocaleglibc"
		StrCmp $BPBIBLELANGUAGE "" BPBibleLanguageCode2
		IfFileExists "${PROGRAMDIRECTORY}\locales\$BPBIBLELANGUAGE\*.*" SetBPBibleLanguage

	BPBibleLanguageCode2:
		; e.g. en, hu
		ReadEnvStr $BPBIBLELANGUAGE "PortableApps.comLocaleCode2"
		StrCmp $BPBIBLELANGUAGE "" BPBibleLanguageSettingsFile
		StrCmp $BPBIBLELANGUAGE "en" SetBPBibleLanguage
		IfFileExists "${PROGRAMDIRECTORY}\locales\$BPBIBLELANGUAGE\*.*" SetBPBibleLanguage

	BPBibleLanguageSettingsFile:
		ReadINIStr $BPBIBLELANGUAGE "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "Language" "LANG"
		StrCmp $BPBIBLELANGUAGE "" SettingsWork
		StrCmp $BPBIBLELANGUAGE "en_US" SetBPBibleLanguage
		IfFileExists "${PROGRAMDIRECTORY}\locales\$BPBIBLELANGUAGE\*.*" SetBPBibleLanguage SettingsWork

	SetBPBibleLanguage:
		; If it's the same as before, don't change it.  This could be useful if the user
		; manually changes the language to something the PortableApps.com Platform doesn't
		; support, such as Vietnamese at the moment.
		${ReadINIStrWithDefault} $LASTBPBIBLELANGUAGE "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "Language" "LastLanguage" "NONE"
		StrCmp $LASTBPBIBLELANGUAGE $BPBIBLELANGUAGE SettingsWork
		WriteINIStr "${SETTINGSDIRECTORY}\data.conf" "Locale" "language" $BPBIBLELANGUAGE
		WriteINIStr "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "Language" "LastLanguage" "$BPBIBLELANGUAGE"

	SettingsWork:
		;=== Create data directories if non-existent
		CreateDirectory "$EXEDIR\Data"
		CreateDirectory "${SETTINGSDIRECTORY}"
		CreateDirectory "${RESOURCESDIRECTORY}"

		; Find The SWORD Project for Windows
		ReadRegStr $LOCALSPRESOURCESDIRECTORY HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\sword.exe" "Path"
		ClearErrors
		StrCmp $LOCALSPRESOURCESDIRECTORY "" "" SkipSetLocalSPResourcesDefault
			StrCpy $LOCALSPRESOURCESDIRECTORY "C:\Program Files\CrossWire\The SWORD Project"

	SkipSetLocalSPResourcesDefault:
		${ReadINIStrWithDefault} $LASTDRIVE "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastDrive" "NONE"
		${ReadINIStrWithDefault} $LASTRESOURCESDIRECTORY "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastResourcesDirectory" "NONE"
		${ReadINIStrWithDefault} $LASTSPPRESOURCESDIRECTORY "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastSWORDProjectPortableResourcesDirectory" "NONE"
		${ReadINIStrWithDefault} $LASTSBPRESOURCESDIRECTORY "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastSwordBiblePortableResourcesDirectory" "NONE"
		${ReadINIStrWithDefault} $LASTLOCALSPRESOURCESDIRECTORY "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastLocalSWORDProjectResourcesDirectory" "NONE"
		StrCmp "${SETTINGSDIRECTORY}" $LASTDRIVE "" FixPaths
		StrCmp "${RESOURCESDIRECTORY}" $LASTRESOURCESDIRECTORY "" FixPaths
		StrCmp $SPPRESOURCESDIRECTORY $LASTSPPRESOURCESDIRECTORY "" FixPaths
		StrCmp $SBPRESOURCESDIRECTORY $LASTSBPRESOURCESDIRECTORY "" FixPaths
		StrCmp $LOCALSPRESOURCESDIRECTORY $LASTLOCALSPRESOURCESDIRECTORY "" FixPaths
		Goto RunProgram ; All paths identical.  Skip path correction.

	FixPaths:
		${GetRoot} $EXEDIR $CURRENTDRIVE
		WriteINIStr "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastDrive" $CURRENTDRIVE
		WriteINIStr "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastResourcesDirectory" ${RESOURCESDIRECTORY}
		WriteINIStr "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastSWORDProjectPortableResourcesDirectory" $SPPRESOURCESDIRECTORY
		WriteINIStr "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastSwordBiblePortableResourcesDirectory" $SBPRESOURCESDIRECTORY
		WriteINIStr "${SETTINGSDIRECTORY}\${NAME}Settings.ini" "${NAME}Settings" "LastLocalSWORDProjectResourcesDirectory" $LOCALSPRESOURCESDIRECTORY
		FlushINI "${SETTINGSDIRECTORY}\${NAME}Settings.ini"
		IfFileExists "${SETTINGSDIRECTORY}\data.conf" "" CreateSwordConf
		WriteINIStr "${SETTINGSDIRECTORY}\data.conf" "Internal" "path" "${SETTINGSDIRECTORY}\data.conf"
		FlushINI "${SETTINGSDIRECTORY}\data.conf"

	CreateSwordConf:
		IfFileExists "${SETTINGSDIRECTORY}\sword.conf" FixSwordPaths
			FileOpen $R0 "${SETTINGSDIRECTORY}\sword.conf" w
			FileClose $R0

	FixSwordPaths:
		; Turn DataPaths into AugmentPaths - we need to use an exclusive DataPath for WriteINIStr
		${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "DataPath=" "AugmentPath="
		; Remove "comment" notation (if the directory doesn't exist, it gets "commented" so that it doesn't appear in the list.)
		${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "DisabledPath=" "AugmentPath="

		;FixSwordPathsSPPResources:
			; Fix SWORD Project Portable paths
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "AugmentPath=$LASTSPPRESOURCESDIRECTORY" "DataPath=$LASTSPPRESOURCESDIRECTORY"
			WriteINIStr "${SETTINGSDIRECTORY}\sword.conf" "Install" "DataPath" "$SPPRESOURCESDIRECTORY"
			FlushINI "${SETTINGSDIRECTORY}\sword.conf"

		;FixSwordPathsSBPResources:
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "DataPath=" "AugmentPath="
			; Fix SwordBible Portable paths
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "AugmentPath=$LASTSBPRESOURCESDIRECTORY" "DataPath=$LASTSBPRESOURCESDIRECTORY"
			WriteINIStr "${SETTINGSDIRECTORY}\sword.conf" "Install" "DataPath" "$SBPRESOURCESDIRECTORY"
			FlushINI "${SETTINGSDIRECTORY}\sword.conf"

		;FixSwordPathsLocalSPResources:
			; Remove DataPaths - we need to use that for the WriteINIStr stuff
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "DataPath=" "AugmentPath="
			; Fix SWORD Project Portable paths
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "AugmentPath=$LASTLOCALSPRESOURCESDIRECTORY" "DataPath=$LASTLOCALSPRESOURCESDIRECTORY"
			WriteINIStr "${SETTINGSDIRECTORY}\sword.conf" "Install" "DataPath" "$LOCALSPRESOURCESDIRECTORY"
			FlushINI "${SETTINGSDIRECTORY}\sword.conf"

			StrCmp $USELOCALSPRESOURCES "true" FixSwordPathsBPBibleResources
			; We're not going to use the local SWORD installation resources, so disable it
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "DataPath=$LOCALSPRESOURCESDIRECTORY" "DisabledPath=$LOCALSPRESOURCESDIRECTORY"

		FixSwordPathsBPBibleResources:
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "DataPath=" "AugmentPath="
			; Make it find BPBible Portable's resources path first
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" "AugmentPath=$LASTRESOURCESDIRECTORY" "DataPath=$LASTRESOURCESDIRECTORY"
			WriteINIStr "${SETTINGSDIRECTORY}\sword.conf" "Install" "DataPath" "${RESOURCESDIRECTORY}"
			FlushINI "${SETTINGSDIRECTORY}\sword.conf"

		;UpdateDriveLetters:
			StrCmp $LASTDRIVE "NONE" RemoveSwordRIFBackup
			StrCmp $LASTDRIVE $CURRENTDRIVE RemoveSwordRIFBackup

			;=== Replace drive letter entries elsewhere
			${ReplaceInFile} "${SETTINGSDIRECTORY}\sword.conf" $2 $3

	RemoveSwordRIFBackup:
		Delete "${SETTINGSDIRECTORY}\sword.conf.old" ; clean up the thing from ReplaceInFile calls

	RunProgram:
		Exec $EXECSTRING
		newadvsplash::stop /WAIT
SectionEnd
