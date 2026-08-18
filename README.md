# MultiMiner

Application Windows avec interface graphique permettant de piloter des
mineurs réels (protocole Stratum) vers un pool de minage de votre
choix — en CPU (Bitcoin), en GPU (Ergo ou OctaSpace selon votre carte),
ou les deux simultanément.

## ⚠️ Avertissement important

Le minage de Bitcoin (SHA-256d) est aujourd'hui réservé au matériel
ASIC spécialisé. **Miner avec un CPU (ou même un GPU grand public)
ne rapportera pas de revenus significatifs** : le coût électrique
dépassera très largement tout gain espéré. Cette application est un
outil réel de connexion à un pool et de suivi de statistiques, pas une
promesse de rentabilité.

L'application ne mine jamais sans action explicite de l'utilisateur,
n'a aucune persistance cachée, ne demande jamais de clé privée ni de
seed phrase, et le processus de minage est toujours visible (y compris
dans le Gestionnaire des tâches Windows).

## Structure du projet

```
MultiMiner/
├── Install.vbs              # ⭐ Installer : double-cliquez ici
├── Uninstall.vbs             # Désinstaller : double-cliquez ici
├── src/                      # Code source de l'application
├── scripts/                  # Installateur/désinstalleur graphiques + outils avancés
├── assets/icon.ico, icon.png # Icône de l'application
├── config/config.json        # Configuration par défaut
├── miner/README.txt          # Infos sur le mineur externe
├── requirements.txt
├── MultiMiner.spec         # Configuration PyInstaller
└── README.md
```

---

## Installation

**Une seule chose à faire : double-cliquez sur `Install.vbs`.**

Une fenêtre s'ouvre (logo, barre de progression, journal, avertissement
de rentabilité) et s'occupe de tout automatiquement, sans aucune
fenêtre de terminal qui s'affiche :

1. vérifie que Python est installé ;
2. télécharge le mineur CPU (`cpuminer-multi`, depuis sa release
   officielle GitHub) ;
3. crée un environnement Python isolé et installe les dépendances ;
4. compile `MultiMiner.exe` ;
5. prépare le dossier `dist\` (icône, désinstalleur, mineur, config) ;
6. crée un raccourci sur le Bureau.

À la fin, cliquez sur **"Lancer MultiMiner"** dans la même fenêtre,
ou utilisez le raccourci créé sur le Bureau.

Si Python n'est pas encore installé : installez **Python 3.10+** depuis
https://www.python.org/downloads/ (cochez "Add Python to PATH"), puis
relancez `Install.vbs`.

### Pourquoi un `.vbs` et pas un `.bat` ?

Un `.bat` fait apparaître brièvement une fenêtre noire de terminal,
même s'il ne fait que lancer autre chose ensuite — ça donne une
impression amateur. `Install.vbs` lance directement l'interface
graphique sans jamais afficher de terminal, comme un vrai installateur
Windows.

## Tester l'application sans miner réellement

1. Lancez `dist\MultiMiner.exe` (ou le raccourci Bureau).
2. Vérifiez que le statut affiche **"Arrêté"** au démarrage.
3. Ouvrez **Paramètres**, laissez les champs pool/wallet vides, cliquez
   sur **Enregistrer** : un message d'erreur clair doit apparaître.
4. Remplissez des valeurs de test mais laissez le champ "Exécutable
   mineur" vide, puis cliquez sur **Démarrer** : l'application doit
   refuser de lancer le minage avec une erreur compréhensible, sans
   jamais planter.
5. Avec une vraie configuration de pool et un exécutable mineur valide,
   cliquez sur **Démarrer** (confirmation demandée à chaque fois) pour
   lancer un minage réel.

## Statistiques temps réel (prix BTC, estimation de gains)

L'application interroge automatiquement, toutes les 60 secondes, le
prix du Bitcoin et le hashrate du réseau via l'API publique
`blockchain.info`, et affiche dans le panneau **"Estimation temps
réel"** :

- le prix BTC actuel ;
- le hashrate du réseau Bitcoin ;
- une estimation du **BTC gagné par jour** à votre hashrate actuel ;
- sa valeur estimée en dollars ;
- le **temps moyen attendu pour trouver un bloc**.

Ce dernier chiffre, en minage CPU, se compte typiquement en milliers de
milliards d'années — l'application l'affiche tel quel plutôt que de le
maquiller, pour rester honnête sur la réalité économique rappelée plus
haut. Ces valeurs sont une espérance statistique, pas une promesse de
revenu.

### Mode de minage : CPU, GPU, ou les deux

Dans **Paramètres**, un sélecteur "Mode de minage" permet de choisir :

- **CPU uniquement** — mine du Bitcoin (SHA-256d) via `cpuminer-multi`.
- **GPU uniquement** — mine de l'Ergo (algorithme Autolykos2) via
  `lolMiner`, un mineur GPU réel, activement maintenu (AMD + NVIDIA).
- **CPU + GPU simultanément** — les deux tournent en parallèle, en
  deux processus indépendants, chacun vers son propre pool et son
  propre wallet.

**Pourquoi Ergo et pas Bitcoin en GPU ?** Il n'existe pas aujourd'hui
de mineur GPU Bitcoin légitime et maintenu : les GPU sont devenus
inutiles pour Bitcoin dès l'arrivée des ASIC vers 2013 (cgminer et
sgminer, les anciens mineurs GPU historiques, ont explicitement
déprécié leur support SHA-256 GPU). lolMiner + Ergo est un choix réel
et vérifié, pas une simulation : Ergo se mine effectivement en GPU
aujourd'hui, avec une rentabilité qui dépend de votre matériel et du
prix de l'électricité — contrairement au CPU/Bitcoin, mathématiquement
non rentable quel que soit le matériel.

Les deux profils nécessitent chacun leur propre wallet (l'un pour
Bitcoin, l'autre pour Ergo) : ce sont deux cryptomonnaies distinctes.

## Rendre l'outil disponible à plusieurs personnes

Chaque personne configure sa propre installation via **Paramètres** :
mode de minage, pool, wallet et worker lui appartiennent en propre. Il
n'y a pas de configuration partagée forcée — chaque copie de
`dist\MultiMiner.exe` (avec son `config\config.json` et son
`miner\`) est indépendante. Pour distribuer à plusieurs personnes,
copiez simplement le dossier `dist\` (voir section suivante) ; chacun
paramètre ensuite son propre pool/wallet au premier lancement.

## Distribuer l'application à un autre PC Windows

1. Copiez `dist\MultiMiner.exe` sur le PC cible.
2. Copiez également le dossier `dist\miner\` (le mineur y est déjà
   présent après l'installation).
3. Aucune installation Python n'est nécessaire sur le PC cible : le
   `.exe` est autonome.

## Désinstaller

**Double-cliquez sur `Uninstall.vbs`** à la racine du projet. Une
fenêtre s'ouvre (logo, confirmation, journal), arrête MultiMiner
s'il tourne encore, supprime le raccourci Bureau, puis supprime
**l'intégralité du dossier MultiMiner** (environnement Python, code
source, mineur, tout) — pas seulement le sous-dossier `dist\`.

Comme ce script se trouve dans le dossier qu'il doit supprimer, la
suppression finale est déléguée à un petit script temporaire (copié
dans `%TEMP%`) qui attend la fermeture de la fenêtre avant d'agir.

Si vous avez seulement distribué le dossier `dist\` à un autre PC (sans
le reste du projet), ce dossier contient son propre `Uninstall.bat`
plus simple qui ne supprime que lui-même.

## Pour les développeurs : compilation en ligne de commande

`Install.vbs` est le point d'entrée recommandé pour un usage normal.
Si vous préférez la ligne de commande (CI, débogage, automatisation),
utilisez `scripts\build_advanced.bat` à la place — il fait exactement
la même chose sans interface graphique :

```
scripts\build_advanced.bat
```

Compilation manuelle, étape par étape :
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pyinstaller MultiMiner.spec
```

**L'exécutable final se trouve dans :**
```
dist\MultiMiner.exe
```

### Mode one-file vs one-folder

Le `.spec` fourni génère un **seul fichier** `MultiMiner.exe`
(mode one-file). C'est le plus simple à distribuer, au prix d'un
démarrage légèrement plus lent (quelques secondes, le temps que
PyInstaller extraie les bibliothèques Qt dans un dossier temporaire).
Un mode alternatif "one-folder", plus rapide au démarrage mais donnant
un dossier complet à distribuer, est documenté en commentaire à la fin
de `MultiMiner.spec`.

## Architecture

- **Interface** : Python + PySide6 (Qt6)
- **Compilation** : PyInstaller (génère un `.exe` autonome)
- **Installateur** : Tkinter (fourni avec Python, aucune dépendance
  externe requise avant l'installation elle-même)
- **Moteur de minage CPU** : `cpuminer-multi`, open source, piloté en
  sous-processus via `QProcess` (Bitcoin, SHA-256d)
- **Moteur de minage GPU** : `lolMiner`, open source, activement
  maintenu, piloté en sous-processus via `QProcess` (Ergo, Autolykos2)
- Aucun protocole de minage n'est réimplémenté par ce projet : ce sont
  deux binaires externes légitimes, chacun piloté indépendamment.

## Sécurité

- Aucune clé privée ni seed phrase n'est jamais demandée ou stockée.
- Seule une **adresse wallet publique** (destination des paiements du
  pool) est configurée, comme sur n'importe quel logiciel de minage
  légitime.
- Le processus de minage est toujours visible et s'arrête proprement
  au clic sur **Arrêter** ou à la fermeture de l'application.
- Aucun lancement automatique caché, aucune persistance au démarrage
  de Windows, aucun contournement d'antivirus.
