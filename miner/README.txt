Ce dossier doit contenir le binaire du mineur externe piloté par
MultiMiner.exe (par exemple cpuminer-multi).

MultiMiner ne réimplémente PAS le protocole de minage : il lance ce
binaire en sous-processus visible, avec les paramètres que vous avez
saisis dans l'onglet Paramètres, et lit sa sortie pour afficher le
hashrate et les shares acceptées.

Comment l'obtenir :

1. Rendez-vous sur le dépôt officiel du projet cpuminer-multi :
   https://github.com/tpruvot/cpuminer-multi
   (ou tout autre mineur CPU open source compatible protocole Stratum
   de votre choix).

2. Téléchargez une release Windows précompilée (fichier .exe), ou
   compilez le projet vous-même à partir des sources selon les
   instructions du dépôt.

3. Placez le fichier .exe obtenu dans ce dossier "miner/", par exemple :
   miner/cpuminer-multi.exe

4. Dans MultiMiner, ouvrez Paramètres > Exécutable mineur, et
   sélectionnez ce fichier via "Parcourir...".

Aucun binaire n'est fourni automatiquement avec ce projet : c'est une
dépendance externe que vous choisissez et téléchargez vous-même, comme
n'importe quel logiciel tiers.
