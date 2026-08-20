' Install.vbs
' Lance l'installateur graphique de MultiMiner sans ouvrir aucune
' fenetre console, meme brievement (contrairement a un .bat classique).

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
installerPath = scriptDir & "\scripts\installer_gui.py"

shell.CurrentDirectory = scriptDir

If fso.FileExists(installerPath) Then
    On Error Resume Next
    shell.Run "pythonw """ & installerPath & """", 0, False
    If Err.Number <> 0 Then
        ' pythonw introuvable dans le PATH : tentative avec python
        Err.Clear
        shell.Run "python """ & installerPath & """", 1, False
    End If
    On Error Goto 0
Else
    MsgBox "Fichier introuvable : " & installerPath, vbCritical, "MultiMiner"
End If
