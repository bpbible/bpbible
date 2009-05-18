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
!define VER "1.6.5.0"
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
!include LogicLib.nsh

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
Var EXECSTRING
Var MISSINGFILEORPATH
Var BPBIBLELANGUAGE

Section "Main"
	${IfNot} ${FileExists} "$EXEDIR\App\${DEFAULTAPPDIR}\${DEFAULTEXE}"
		;=== Program executable not where expected
		StrCpy $MISSINGFILEORPATH ${DEFAULTEXE}
		MessageBox MB_OK|MB_ICONEXCLAMATION `$(LauncherFileNotFound)`
		Abort
	${EndIf}

	;=== Read the parameters from the INI file
	${ReadINIStrWithDefault} $0 "$EXEDIR\${NAME}.ini" "${NAME}" "DisableSplashScreen" "false"

	${If} $0 != "true"
		;=== Show the splash screen while processing data
		InitPluginsDir
		File /oname=$PLUGINSDIR\splash.jpg "${NAME}.jpg"
		newadvsplash::show /NOUNLOAD 2000 0 0 -1 /L $PLUGINSDIR\splash.jpg
	${EndIf}

	;=== Get any passed parameters
	StrCpy $EXECSTRING `"$EXEDIR\App\${DEFAULTAPPDIR}\${DEFAULTEXE}" --data-path="$EXEDIR\Data\settings" --index-path="$EXEDIR\Data\resources" --sword-path="$EXEDIR\Data\settings"`

	${GetParameters} $0
	${IfThen} $0 != "" ${|} StrCpy $EXECSTRING "$EXECSTRING $0" ${|}

	${ReadINIStrWithDefault} $0 "$EXEDIR\${NAME}.ini" "${NAME}" "AdditionalParameters" ""
	${IfThen} $0 != "" ${|} StrCpy $EXECSTRING "$EXECSTRING $0" ${|}

	;=== Set the language
		; GLIBC: e.g. en_US, hu
		ReadEnvStr $BPBIBLELANGUAGE "PortableApps.comLocaleglibc"
		${If} $BPBIBLELANGUAGE == ""
		${OrIfNot} ${FileExists} "$EXEDIR\App\${DEFAULTAPPDIR}\locales\$BPBIBLELANGUAGE\*.*"
			; Code 2: e.g. en, hu
			ReadEnvStr $BPBIBLELANGUAGE "PortableApps.comLocaleCode2"
			${If} $BPBIBLELANGUAGE != "en"
				${If} $BPBIBLELANGUAGE == ""
				${OrIfNot} ${FileExists} "$EXEDIR\App\${DEFAULTAPPDIR}\locales\$BPBIBLELANGUAGE\*.*"
					ReadINIStr $BPBIBLELANGUAGE "$EXEDIR\Data\settings\${NAME}Settings.ini" "Language" "LANG"
					${IfThen} $BPBIBLELANGUAGE == "en_US" ${|} StrCpy $BPBIBLELANGUAGE "en" ${|}
					${IfNotThen} ${FileExists} "$EXEDIR\App\${DEFAULTAPPDIR}\locales\$BPBIBLELANGUAGE\*.*" ${|} StrCpy $BPBIBLELANGUAGE "en" ${|}
				${EndIf}
			${EndIf}
		${EndIf}

		${ReadINIStrWithDefault} $0 "$EXEDIR\Data\settings\${NAME}Settings.ini" "Language" "LastLanguage" "NONE"
		${If} $BPBIBLELANGUAGE != ""
		${AndIf} $0 != $BPBIBLELANGUAGE
			; If it's the same as before, don't change it.  This could be useful if the user
			; manually changes the language to something the PortableApps.com Platform doesn't
			; support, such as Vietnamese at the moment.
			WriteINIStr "$EXEDIR\Data\settings\data.conf" "Locale" "language" $BPBIBLELANGUAGE
			WriteINIStr "$EXEDIR\Data\settings\${NAME}Settings.ini" "Language" "LastLanguage" $BPBIBLELANGUAGE
		${EndIf}

	;=== Work with the settings
		;=== Create data directories if non-existent
		CreateDirectory "$EXEDIR\Data"
		CreateDirectory "$EXEDIR\Data\settings"
		CreateDirectory "$EXEDIR\Data\resources"
		CopyFiles /SILENT "$EXEDIR\App\DefaultData\settings\*.*" "$EXEDIR\Data\settings"

		;=== Update drive letters:
		${ReadINIStrWithDefault} $0 "$EXEDIR\Data\settings\${NAME}Settings.ini" "${NAME}Settings" "LastResourcesDirectory" "NONE"
		${If} $0 == "$EXEDIR\Data\resources"
			${ReplaceInFile} "$EXEDIR\Data\settings\sword.conf" "DataPath=" "AugmentPath="
			; Make it find BPBible Portable's resources path first
			${ReplaceInFile} "$EXEDIR\Data\settings\sword.conf" "AugmentPath=$0" "DataPath=$0"
			WriteINIStr "$EXEDIR\Data\settings\sword.conf" "Install" "DataPath" "$EXEDIR\Data\resources"
			FlushINI "$EXEDIR\Data\settings\sword.conf"
		${EndIf}

		; $0 = last, $1 = current
		${ReadINIStrWithDefault} $0 "$EXEDIR\Data\settings\${NAME}Settings.ini" "${NAME}Settings" "LastDrive" "NONE"
		${GetRoot} $EXEDIR $1
		${If} $0 != $1
			WriteINIStr "$EXEDIR\Data\settings\${NAME}Settings.ini" "${NAME}Settings" "LastDrive" $1
			WriteINIStr "$EXEDIR\Data\settings\${NAME}Settings.ini" "${NAME}Settings" "LastResourcesDirectory" "$EXEDIR\Data\resources"
			${If} ${FileExists} "$EXEDIR\Data\settings\data.conf"
				WriteINIStr "$EXEDIR\Data\settings\data.conf" "Internal" "path" "$EXEDIR\Data\settings\data.conf"
				FlushINI "$EXEDIR\Data\settings\data.conf"
			${EndIf}

			;=== Replace drive letter entries elsewhere
			${ReplaceInFile} "$EXEDIR\Data\settings\sword.conf" $0 $1
			Delete "$EXEDIR\Data\settings\sword.conf.oldReplaceInFile"
		${EndIf}

	;=== run the program:
		Exec $EXECSTRING
		newadvsplash::stop /WAIT
SectionEnd
