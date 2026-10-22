# SGD — Gestion Restaurant

## Résumé

SGD est une application de bureau Python destinée au suivi des revenus et dépenses d’un restaurant. Elle est prévue pour un usage individuel et local, sur un ordinateur ; elle n’a pas vocation à être publiée ni téléchargée sur Internet. L’interface principale utilise Tkinter et les données sont stockées dans une base SQLite locale (`restaurant.db`). Une version Windows empaquetée existe dans `dist/GestionRestaurant.exe`.

## Fonctionnalités repérées

- Accueil/tableau de bord avec aperçu financier et graphiques.
- Saisie et consultation des revenus et des dépenses.
- Catégories et types de dépenses.
- Rapports filtrés par type, catégorie et période, avec export PDF et Excel.
- Profils locaux permettant de distinguer les données.
- Suppression d’opérations depuis les paramètres.

Ce résumé décrit le code présent ; les fonctionnalités doivent encore être essayées dans l’application.

## Organisation du dossier

| Fichier ou dossier | Rôle observé |
|---|---|
| `main.py` | Point d’entrée et navigation principale. |
| `accueil.py` | Tableau de bord. |
| `depenses.py`, `revenus.py` | Gestion des dépenses et revenus. |
| `rapport.py` | Rapports et exports PDF/Excel. |
| `database.py` | Initialisation SQLite et accès aux données. |
| `restaurant.db` | Base locale existante ; données à préserver. |
| `comptes.json` | Liste de noms ; usage par l’application principale à clarifier. |
| `avecRESPON/` | Variante responsive séparée, à évaluer. |
| `deptext.py` | Autre module de rapport ; rôle par rapport à `rapport.py` à clarifier. |
| `*.txt` | Plusieurs sont des copies exactes de modules `.py`; `main.txt` diffère de `main.py`. |
| `*.spec`, `build/`, `dist/` | Configuration et artefacts de compilation PyInstaller. |
| `SGD.png`, `SGD.ico` | Logo et icône. |

## Technologies

- Python, Tkinter et SQLite (`sqlite3`).
- Bibliothèques détectées : `tkcalendar`, `matplotlib`, `reportlab`, `openpyxl`.
- Pillow (`PIL`) est utilisé pour certaines images, avec une solution de repli si indisponible.
- PyInstaller pour construire l’exécutable Windows.

Aucun `requirements.txt` ni README n’était présent avant cette synthèse ; les versions exactes des dépendances ne sont donc pas documentées.

## Lancement observé

Depuis PowerShell, avec Python et les dépendances installées :

```powershell
cd "C:\Users\YG TECH\Desktop\MAC"
python main.py
```

En développement, la base est dans `%LOCALAPPDATA%\SGD\Data\restaurant.db` sous Windows (ou dans `~/AppData/Local/SGD/Data/restaurant.db` si `LOCALAPPDATA` n'est pas défini). `SGD_DATA_DIR` permet de choisir un autre dossier. L'application n'importe jamais le fichier `restaurant.db` du projet et ne l'embarque pas dans l'exécutable : une installation neuve crée sa propre base vide et demande la création du premier compte.

## Compilation et livraison Windows

### Créer les fichiers de livraison sur le PC de développement

1. Installez PyInstaller dans l'environnement Python contenant les dépendances : `python -m pip install pyinstaller`.
2. Depuis la racine du projet, exécutez `powershell -ExecutionPolicy Bypass -File .\build_windows.ps1`. Cela crée l'application `dist\GestionRestaurant.exe` et son manifeste de compilation.
3. Créez l'installateur autonome : `powershell -ExecutionPolicy Bypass -File .\installer\build_installer.ps1`. Le fichier destiné au client est `release\SGD-Setup.exe`.
4. Livrez uniquement `SGD-Setup.exe`. Le paquet comprend l'application et son installateur, mais n'embarque ni `restaurant.db`, ni `.env`, ni les sources de développement. Ne distribuez pas directement l'ancien EXE dans `dist`.

### Installation sur le PC du client

Le client lance `SGD-Setup.exe` et accepte l'invite UAC. Une fenêtre de commande visible demande éventuellement l'adresse Gmail et le mot de passe d'application ; en cas d'erreur, elle reste ouverte pour afficher le message. SGD est installé dans `C:\Program Files\SGB`. L'installateur crée un raccourci sur le Bureau, mais **aucune base de données sur le Bureau**. La base neuve est créée au premier lancement sous `C:\Program Files\SGB\Data\restaurant.db`. Le client ouvre SGD depuis le raccourci et crée son premier compte.

Windows protège `Program Files`; l'installateur accorde donc les droits d'écriture sur `Data` au compte Windows qui réalise l'installation. Utilisez le profil Windows du client pendant l'élévation UAC. La configuration Gmail est facultative : sans elle, l'application fonctionne, mais ne peut pas envoyer les codes de récupération. Pour activer l'envoi, saisissez le compte expéditeur et son mot de passe d'application Google durant l'installation. Le secret est chiffré par DPAPI et stocké séparément dans `%APPDATA%\SGD\.env` pour ce profil Windows. Testez l'envoi Gmail sur le PC cible.

Une installation sur un nouveau PC crée sa propre base. Une réinstallation sur le même PC conserve la base existante. Sauvegardez-la avant toute maintenance. La base reste dans `C:\Program Files\SGB\Data`, jamais sur le Bureau.

**Limite :** l'accès en écriture à la base est accordé au compte ayant installé SGD. Si plusieurs profils Windows différents doivent utiliser SGD sur un seul PC, il faudra adapter ces permissions ou définir un emplacement de données partagé.

## Livraison macOS

La compilation et la création du disque d'installation macOS doivent être réalisées sur un Mac, avec Python, les dépendances de l'application, PyInstaller, Xcode Command Line Tools (`sips` et `iconutil`) et `hdiutil` disponibles. Depuis le dossier du projet sur le Mac, lancez :

```bash
chmod +x build_macos.sh
./build_macos.sh
```

Le résultat est `release/SGD-macOS.dmg`. Ouvrez ce disque et faites glisser `SGD.app` vers `Applications`. Le disque comprend un raccourci vers le dossier Applications ; il ne crée pas de raccourci sur le Bureau. Au premier lancement, macOS peut demander de confirmer l'ouverture d'une application téléchargée.

La base de données et la configuration locale sont séparées de l'application et enregistrées dans `~/Library/Application Support/SGD/` (respectivement `Data/restaurant.db` et `.env`). Le fichier de base n'a pas d'attribut « caché », mais son dossier parent `~/Library` est normalement masqué dans Finder. Le DMG n'inclut aucune base de développement ni aucun fichier `.env`.


**Dépannage Windows :** si aucune fenêtre n'apparaît, vérifiez que les fenêtres de connexion/création initiales restent visibles lorsque la fenêtre racine est masquée.


## Données et usage individuel

Il n’y a pas de serveur ni de synchronisation en ligne prévus. La base locale contient les comptes/profils et les opérations financières : la sauvegarder avant toute mise à jour. L’application demande une authentification au démarrage et stocke les mots de passe sous forme de hash PBKDF2, pas en clair; il est donc impossible d’afficher un ancien mot de passe. Après connexion, le changement de mot de passe se trouve dans Paramètres et vérifie l’ancien mot de passe. Les comptes supplémentaires ne peuvent pas être créés depuis cet écran; la création du premier compte reste proposée au premier lancement. Sur l’écran de connexion, « Mot de passe oublié ? » guide la récupération en trois étapes distinctes : vérification de l’adresse e-mail du compte et envoi du code, validation du code reçu, puis choix du nouveau mot de passe. Les champs du code et du nouveau mot de passe ne s’affichent qu’à l’étape correspondante. Le code expire après 10 minutes et est limité à cinq essais; le mot de passe ne peut pas être changé avant validation du code. L’envoi exige une configuration SMTP (voir ci-dessous); sans elle, le parcours affiche une erreur et ne réinitialise pas le mot de passe. Les comptes restent locaux à cette base : ne partagez pas de vrais mots de passe ou renseignements personnels dans des sources ou rapports de diagnostic.

### Configuration de la récupération par e-mail

Pour l'installation Windows, `release\SGD-Setup.exe` demande facultativement le compte Gmail expéditeur et son mot de passe d'application avant l'élévation UAC, puis enregistre les paramètres dans `%APPDATA%\SGD\.env`, jamais dans le programme compilé; le mot de passe est chiffré par Windows DPAPI et lié au profil Windows qui lance l'installateur. Pour préparer Gmail, activez la validation en deux étapes sur le compte expéditeur Google, créez un **mot de passe d'application Google**, puis saisissez ce mot de passe dans l'installateur. Le mot de passe normal du compte Gmail n'est pas pris en charge. Le fichier `.env.example` ne contient que des valeurs fictives. Ne partagez et ne publiez jamais votre fichier `.env` ou le mot de passe d'application.

- `SGD_SMTP_HOST` : `smtp.gmail.com`.
- `SGD_SMTP_PORT` : `587` (STARTTLS).
- `SGD_SMTP_USER` : adresse Gmail expéditrice.
- `SGD_SMTP_PASSWORD` : mot de passe d'application Google, pas le mot de passe Gmail.
- `SGD_SMTP_FROM` : même adresse Gmail.

Si l'adresse est laissée vide dans l'installateur, il n'y aura pas d'envoi de courriel avant configuration SMTP. L'envoi réel doit être vérifié sur le poste avec un compte Gmail et un mot de passe d'application valides; aucun identifiant n'est fourni ou intégré à ce dépôt.

Le message est envoyé à l’adresse enregistrée pour le compte. Le code de six chiffres est conservé uniquement en mémoire (sous forme de hash), expire après 10 minutes, est limité à cinq essais et doit être confirmé avant toute réinitialisation. Si l’application est fermée, demandez un nouveau code.

## Priorités proposées pour la reprise

### 1. Protéger les données

- Faire une copie intacte de `restaurant.db` avant toute intervention.
- Choisir un emplacement local stable pour la base, indépendant du dossier courant et du répertoire temporaire PyInstaller.
- Éviter qu’une mise à jour ou un lancement depuis un autre répertoire crée une base vide à la place de l’existante.
- Ajouter une commande ou fonction simple de sauvegarde/restauration et documenter la procédure.

### 2. Établir l’état de référence

- Démarrer l’application avec une copie de la base et vérifier chaque écran.
- Tester ajout, consultation, filtres, export, changement de profil et suppression.
- Noter les anomalies avant de modifier l’interface ou le schéma de la base.

### 3. Stabiliser le projet

- Ajouter `requirements.txt` avec les dépendances et versions réellement testées.
- Documenter des commandes reproductibles de lancement et de compilation.
- Ajouter des tests des fonctions SQLite et des calculs, sans ouvrir Tkinter.
- Clarifier les fichiers doublons et variantes (`*.txt`, `main.txt`, `deptext.py`, `avecRESPON/`) avant d’en supprimer ou fusionner.

### 4. Améliorer l’usage quotidien

Après stabilisation : validation des dates et montants, messages d’erreur, confirmation avant suppression, affichage/redimensionnement, puis améliorations des rapports selon les besoins réels.

## Journal des évolutions

| Date | Modification | Vérification |
|---|---|---|
| 2026-09-27 | Création de cette synthèse et proposition d’une feuille de route. | Inventaire et lecture des modules principaux ; l’application n’a pas été modifiée. |
| 2026-10-02 | Correction du démarrage Tkinter : les fenêtres de connexion/création initiales restent visibles même lorsque la racine est masquée; mise à jour des consignes de lancement et de stockage des données. | Reproduction Tkinter Windows; compilation des fichiers; tests UI automatisés confirmant que les dialogues création de compte, sélection de compte, et mot de passe sont visibles. |
| 2026-10-02 | Restauration de la récupération par code envoyé à l’adresse e-mail du compte, avec configuration SMTP; ajout de la création de compte depuis l’écran de connexion en réutilisant le formulaire des paramètres. | Vérifications de syntaxe Python et du parcours sur base temporaire; envoi réel de courrier non testé car aucun SMTP n’est configuré dans cet environnement. |
| 2026-10-02 | Ajustement automatique des largeurs dans les exports Excel de `rapport.py` (minimum 10, maximum 50 caractères), et affichage du total des revenus dans des cellules distinctes, y compris lorsqu’il est nul. | Compilation Python et tests de classeurs temporaires avec libellés courts/longs, cellules fusionnées et total des revenus avec/sans données. |
| 2026-10-02 | Clarification de la récupération en trois étapes visibles : vérifier l’adresse, envoyer puis valider le code, et enfin définir le nouveau mot de passe. Le stockage vérifie séparément le code confirmé avant d’autoriser la modification. | Compilation `main.py` et `database.py` réussie; test sur SQLite temporaire : changement bloqué avant code valide, code incorrect refusé, code correct accepté puis nouveau mot de passe haché enregistré. Envoi réel Mailtrap non testé sans identifiants SMTP renseignés. |

**Prudence :** avant toute modification de `database.py`, du schéma ou des chemins, travailler sur une copie de `restaurant.db`. Ne supprimer aucun fichier historique ou de données tant que son rôle n’est pas établi.
