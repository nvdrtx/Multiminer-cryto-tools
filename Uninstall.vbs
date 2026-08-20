' Uninstall.vbs
' Lance l'interface graphique de desinstallation de MultiMiner sans
' ouvrir aucune fenetre console.

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
uninstallerPath = scriptDir & "\scripts\uninstaller_gui.py"

shell.CurrentDirectory = scriptDir

If fso.FileExists(uninstallerPath) Then
    On Error Resume Next
    shell.Run "pythonw """ & uninstallerPath & """", 0, False
    If Err.Number <> 0 Then
        Err.Clear
        shell.Run "python """ & uninstallerPath & """", 1, False
    End If
    On Error Goto 0
Else
    MsgBox "Fichier introuvable : " & uninstallerPath, vbCritical, "MultiMiner"
End If
