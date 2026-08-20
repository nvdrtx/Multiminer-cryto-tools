Ce dossier doit contenir lolMiner.exe, le mineur GPU externe piloté
par MultiMiner en mode "GPU" ou "CPU + GPU".

Il est normalement téléchargé automatiquement (voir Install.vbs /
scripts/fetch_gpu_miner.ps1) depuis le dépôt officiel :
https://github.com/Lolliedieb/lolMiner-releases

Si le téléchargement automatique a échoué (pas de connexion Internet
au moment de l'installation, pare-feu, etc.), téléchargez manuellement
la dernière release Windows (fichier .zip, ex. lolMiner_vX.XX_Win64.zip)
depuis ce dépôt, extrayez lolMiner.exe, et placez-le ici.

Dans MultiMiner, ouvrez Paramètres > Exécutable mineur GPU, et
sélectionnez ce fichier via "Parcourir...".

Pourquoi Ergo (Autolykos2) et pas Bitcoin en GPU ? Il n'existe pas
aujourd'hui de mineur GPU Bitcoin (SHA-256d) légitime et maintenu :
les GPU sont devenus inutiles pour Bitcoin dès l'arrivée des ASIC vers
2013. lolMiner + Ergo est un choix réel, vérifié, activement maintenu.
