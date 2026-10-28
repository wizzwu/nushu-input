Unicode true
!include MUI2.nsh
!include LogicLib.nsh
!include x64.nsh
!include WinVer.nsh
Name "女书输入法 0.1.0 试用版"
OutFile "..\..\dist\NushuInput-Setup.exe"
InstallDir "$LOCALAPPDATA\NushuInput"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_TEXT "女书方案已安装。按 Win+空格切换到小狼毫，再使用 Ctrl+反引号选择女书方案。系统可能需要重新登录。使用说明位于开始菜单的女书输入法文件夹。"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\.build\windows-license.txt"
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

Function .onInit
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "需要 Windows 10 或更新版本。"
    Abort
  ${EndIf}
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "需要 Intel/AMD 64 位 Windows。"
    Abort
  ${EndIf}
  ${If} ${IsNativeARM64}
    MessageBox MB_ICONSTOP "此试用版适配 Intel/AMD 64 位电脑，暂不支持 Windows ARM。"
    Abort
  ${EndIf}
FunctionEnd

Section "安装女书输入法"
  SetOutPath "$INSTDIR"
  File /r "..\..\.build\windows-payload\*"
  DetailPrint "正在安装输入法和部署女书方案，首次安装可能弹出管理员授权。"
  ClearErrors
  ExecWait '"$INSTDIR\runtime\pythonw.exe" "$INSTDIR\install_user.py"' $0
  ${If} ${Errors}
    MessageBox MB_ICONSTOP "无法启动安装程序，请查看 $INSTDIR。"
    SetErrorLevel 1
    Abort
  ${EndIf}
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "安装未完成，请查看 $INSTDIR\install.log。可以重新运行安装程序重试。"
    SetErrorLevel 1
    Abort
  ${EndIf}
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NushuInput" "DisplayName" "女书输入法 0.1.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NushuInput" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NushuInput" "InstallLocation" "$INSTDIR"
  CreateDirectory "$SMPROGRAMS\女书输入法"
  CreateShortCut "$SMPROGRAMS\女书输入法\使用说明.lnk" "$INSTDIR\使用说明.txt"
  CreateShortCut "$SMPROGRAMS\女书输入法\修复配置.lnk" "$INSTDIR\runtime\pythonw.exe" '$\"$INSTDIR\install_user.py$\"'
  CreateShortCut "$SMPROGRAMS\女书输入法\卸载安装工具.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  ; Preserve Rime, all user dictionaries, backups and the shared font.
  ; Delete only this application's private payload (no user-editable Rime data).
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\shared"
  RMDir /r "$INSTDIR\fonts"
  RMDir /r "$INSTDIR\licenses"
  Delete "$INSTDIR\weasel.exe"
  Delete "$INSTDIR\install_user.py"
  Delete "$INSTDIR\install-result.json"
  Delete "$INSTDIR\使用说明.txt"
  Delete "$INSTDIR\resource-manifest.json"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$SMPROGRAMS\女书输入法\使用说明.lnk"
  Delete "$SMPROGRAMS\女书输入法\修复配置.lnk"
  Delete "$SMPROGRAMS\女书输入法\卸载安装工具.lnk"
  RMDir "$SMPROGRAMS\女书输入法"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NushuInput"
  MessageBox MB_OK "安装工具已卸载。女书方案、输入法程序和个人词库已保留；可在小狼毫输入法设置中取消勾选女书。"
SectionEnd
