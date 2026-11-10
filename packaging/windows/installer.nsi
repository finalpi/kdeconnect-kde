; SPDX-License-Identifier: GPL-3.0-only
Unicode True
!include "MUI2.nsh"
!include "x64.nsh"
Name "KDE Connect Native Clipboard ${VERSION}"
OutFile "${OUTPUT}"
InstallDir "$PROGRAMFILES64\KDE Connect"
RequestExecutionLevel admin
; The full official installer is already compressed; avoid recompressing 90 MiB.
SetCompress off
VIProductVersion "26.8.2.1"
VIAddVersionKey /LANG=1033 "ProductName" "KDE Connect Native Clipboard"
VIAddVersionKey /LANG=1033 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "FileDescription" "Complete KDE Connect fork installer"
VIAddVersionKey /LANG=1033 "FileVersion" "26.8.2.1"
VIAddVersionKey /LANG=1033 "LegalCopyright" "KDE Connect contributors; GPL"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${SOURCE}\LICENSES\GPL-3.0-only.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

Function .onInit
    ${IfNot} ${RunningX64}
        MessageBox MB_ICONSTOP "This build requires 64-bit Windows."
        Abort
    ${EndIf}
FunctionEnd

Section "KDE Connect (complete client)"
    InitPluginsDir
    SetOutPath "$PLUGINSDIR"
    File /oname=official.exe "${BASE}"
    File /oname=kdeconnect_clipboard.dll "${COMPONENT}"
    File /oname=fork-build.json "${INFO}"
    File "${SOURCE}\packaging\windows\install_fork.ps1"
    nsExec::ExecToLog '"$WINDIR\SysNative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\install_fork.ps1" -PayloadDirectory "$PLUGINSDIR" -Destination "$INSTDIR"'
    Pop $0
    DetailPrint "Installer engine result: $0"
    FileOpen $1 "$TEMP\kdeconnect-native-install-result.txt" w
    FileWrite $1 "Installer engine result: $0$\r$\n"
    FileClose $1
    StrCmp $0 "0" installed
    SetErrorLevel 1
    MessageBox MB_ICONSTOP "Installation failed (engine result: $0). See the installer details." /SD IDOK
    Abort
installed:
    SetErrorLevel 0
SectionEnd
