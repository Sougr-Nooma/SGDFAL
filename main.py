from accueil import Accueil
import tkinter as tk
from tkinter import ttk, messagebox
import database  # 👈 IMPORTATION CENTRALE DE TOUTE LA LOGIQUE BD
from depenses import Depenses 
from revenus import Revenus
from rapport import Rapport
import sys
import os
import base64
import ctypes
import ctypes.wintypes
import platform
from pathlib import Path
import hmac
import secrets
import time
import smtplib
import ssl
from email.message import EmailMessage

def _dechiffrer_mot_de_passe_dpapi(valeur):
    """Déchiffre un secret créé pour le profil Windows courant avec DPAPI."""
    if os.name != "nt":
        raise OSError("Les secrets SMTP DPAPI sont disponibles sous Windows uniquement.")

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    chiffre = base64.b64decode(valeur, validate=True)
    tampon = ctypes.create_string_buffer(chiffre)
    blob_entree = DataBlob(len(chiffre), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_byte)))
    blob_sortie = DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DataBlob),
        ctypes.POINTER(ctypes.wintypes.LPWSTR),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = ctypes.wintypes.BOOL
    if not crypt32.CryptUnprotectData(
        ctypes.byref(blob_entree), None, None, None, None, 0, ctypes.byref(blob_sortie)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        clair = ctypes.string_at(blob_sortie.pbData, blob_sortie.cbData)
        return clair.decode("utf-8")
    finally:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(blob_sortie.pbData)


def charger_configuration_locale():
    """Charge la configuration privée de l'utilisateur ou le .env de développement."""
    if sys.platform == "darwin":
        repertoire_utilisateur = Path.home() / "Library" / "Application Support" / "SGD"
    else:
        repertoire_utilisateur = Path(
            os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        ) / "SGD"
    fichiers_configuration = [repertoire_utilisateur / ".env"]
    if not getattr(sys, "frozen", False):
        fichiers_configuration.append(Path(__file__).resolve().parent / ".env")

    for configuration in fichiers_configuration:
        try:
            lignes = configuration.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            cle, valeur = ligne.split("=", 1)
            cle, valeur = cle.strip(), valeur.strip()
            if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in ("'", '\"'):
                valeur = valeur[1:-1]
            if cle == "SGD_SMTP_PASSWORD_DPAPI":
                if not valeur:
                    continue
                try:
                    valeur = _dechiffrer_mot_de_passe_dpapi(valeur)
                except (OSError, ValueError, ctypes.ArgumentError) as erreur:
                    print(f"Configuration Gmail DPAPI indisponible pour cet utilisateur Windows : {erreur}")
                    continue
                cle = "SGD_SMTP_PASSWORD"
            if cle and cle not in os.environ:
                os.environ[cle] = valeur


def resource_path(relative_path):
    """Retourne le chemin d'une ressource en développement ou dans PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return os.path.join(base_path, relative_path)


def configurer_icone_fenetre(root):
    """Applique l'icône SGD pour remplacer l'icône Python par défaut."""
    try:
        root.iconbitmap(resource_path("SGD.ico"))
    except tk.TclError:
        try:
            root._sgd_icon_photo = tk.PhotoImage(file=resource_path("SGD.png"))
            root.iconphoto(True, root._sgd_icon_photo)
        except tk.TclError as erreur:
            print(f"Impossible de charger l'icône SGD : {erreur}")


charger_configuration_locale()
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("SGD - Gestion Restaurant")
        self.root.geometry("1000x700")
        # Utiliser le logo SGD au lieu de l'icône Python par défaut.
        configurer_icone_fenetre(self.root)

        # Initialiser la base de données via database.py
        database.init_db()

        # Aucun compte n'est considéré connecté avant vérification du mot de passe.
        self.compte_actif = None
        self.langue = "FR"

        # === BARRE DE NAVIGATION ===
        nav_frame = tk.Frame(root, bg="#2c3e50", height=60)
        nav_frame.pack(side="top", fill="x")

        # Frame contenant logo + texte "SGD"
        sgd_frame = tk.Frame(nav_frame, bg="#2c3e50")
        sgd_frame.pack(side="left", padx=20, pady=10)

        # Charger et afficher le logo
        try:
            from PIL import Image, ImageTk
            logo_img = Image.open(resource_path("SGD.png"))
            logo_img = logo_img.resize((32, 32))  # Ajustez la taille si besoin
            self.logo_tk = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(sgd_frame, image=self.logo_tk, bg="#2c3e50")
            logo_label.pack(side="left")
        except Exception as e:
            print("Erreur chargement logo :", e)
            # Optionnel : afficher un placeholder si le logo n’est pas trouvé
            logo_label = tk.Label(sgd_frame, text="🖼️", font=("Arial", 16), bg="#2c3e50", fg="white")
            logo_label.pack(side="left")

        # Texte "SGD" à côté du logo
        text_label = tk.Label(sgd_frame, text="SGD", font=("Arial", 18, "bold"), fg="white", bg="#2c3e50")
        text_label.pack(side="left", padx=(8, 0))  # Espace entre logo et texte

        btns_frame = tk.Frame(nav_frame, bg="#2c3e50")
        btns_frame.pack(side="left", expand=True)

        buttons = [
            ("Accueil", "accueil"),
            ("Revenus", "revenus"),
            ("Dépenses", "depenses"),
            ("Rapport", "rapport")
        ]

        for text, page in buttons:
            btn = tk.Button(btns_frame, text=text, font=("Arial", 12), bg="#34495e", fg="white", relief="flat", padx=15, command=lambda p=page: self.show_frame(p))
            btn.pack(side="left", padx=15)

        self.btn_parametres = tk.Button(nav_frame, text="⚙️", font=("Arial", 16), bg="#34495e", fg="white", relief="flat", padx=10, command=self.ouvrir_fenetre_parametres)
        self.btn_parametres.pack(side="right", padx=20)

        # === ESPACE PRINCIPAL ===
        self.container = tk.Frame(root, bg="white")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in ("accueil", "revenus", "depenses", "rapport"):
            frame = tk.Frame(self.container, bg="white")
            self.frames[F] = frame
            frame.place(relwidth=1, relheight=1)

        # Masquer l'application jusqu'à l'authentification.
        self.root.withdraw()
        comptes = database.get_all_comptes()
        if comptes:
            self.selectionner_compte(initial=True)
        else:
            messagebox.showinfo("Bienvenue", "Aucun compte n'existe encore. Créez le premier compte pour commencer.")
            self.ajouter_compte(
                on_success=self._connexion_initiale,
                on_cancel=self.root.destroy,
            )

    def _connexion_initiale(self, nom_compte):
        """Ouvre l'application après la création sécurisée du premier compte."""
        self.compte_actif = nom_compte
        self.root.deiconify()
        self.show_frame("accueil")

    def configure_platform(self):
        """Configure l'apparence selon la plateforme"""
        
        # Couleurs de base pour tous les systèmes
        colors = {
            'bg': '#f0f0f0',
            'fg': '#000000',
            'entry_bg': 'white',
            'button_bg': '#e0e0e0',
            'select_bg': '#0078d7',
            'select_fg': 'white'
        }
        
        # Configuration globale
        self.root.option_add('*Background', colors['bg'])
        self.root.option_add('*Foreground', colors['fg'])
        self.root.option_add('*Entry.Background', colors['entry_bg'])
        self.root.option_add('*Text.Background', colors['entry_bg'])
        self.root.option_add('*Listbox.Background', colors['entry_bg'])
        self.root.option_add('*selectBackground', colors['select_bg'])
        self.root.option_add('*selectForeground', colors['select_fg'])
        
        # Configuration ttk
        style = ttk.Style()
        
        if platform.system() == 'Darwin':
            # Sur macOS, éviter le thème 'aqua'
            style.theme_use('clam')
        else:
            # Windows/Linux
            style.theme_use('clam')  # ou 'default'
        
        # Styles ttk personnalisés
        style.configure('TFrame', background=colors['bg'])
        style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
        style.configure('TButton', background=colors['button_bg'])
        style.configure('TEntry', fieldbackground=colors['entry_bg'])
        
    def ouvrir_fenetre_parametres(self):
        """Ouvre une fenêtre modale juste en dessous du bouton Paramètres"""
        fenetre = tk.Toplevel(self.root)
        fenetre.title("Paramètres")
        fenetre.geometry("300x400")
        fenetre.resizable(False, False)
        fenetre.transient(self.root)
        fenetre.grab_set()
        fenetre.configure(bg="#f0f0f0")

        # Vérifie que le bouton est bien affiché à l'écran
        self.root.update_idletasks()  # Force le calcul du layout

        # Calculer la position centrée par rapport à la fenêtre principale
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()

        # Dimensions de la fenêtre paramètres
        param_width = 300
        param_height = 400

        # Calculer la position pour centrer horizontalement et aligner en bas
        x = main_x + (main_width - param_width)
        y = main_y + 85  # Position fixe en bas de la barre de navigation

        # Appliquer la position
        fenetre.geometry(f"{param_width}x{param_height}+{x}+{y}")

        frame_central = tk.Frame(fenetre, bg="#f0f0f0")
        frame_central.pack(expand=True, padx=20, pady=20)

        # Avatar gris
        avatar_canvas = tk.Canvas(frame_central, width=40, height=40, bg="#f0f0f0", highlightthickness=0)
        avatar_canvas.create_oval(5, 5, 35, 35, fill="#ccc", outline="#aaa", width=2)
        avatar_canvas.pack(pady=10)

        # Nom du compte actif
        nom_label = tk.Label(frame_central, text=f"{self.compte_actif}", font=("Arial", 14, "bold"), bg="#f0f0f0")
        nom_label.pack(pady=5)

        titre = tk.Label(frame_central, text="Paramètres", font=("Arial", 14, "bold"), bg="#f0f0f0")
        titre.pack(pady=10)

        
        # === MODIFICATION ICI : Bouton "Changer de compte" ===
        def ouvrir_changer_compte():
            position = fenetre.geometry()  # Récupérer la position actuelle
            fenetre.destroy()  # Fermer la fenêtre paramètres
            self.selectionner_compte(position=position)  # Ouvrir avec la même position

        btn_changer = tk.Button(frame_central, text="🔄 Changer de compte", font=("Arial", 10), bg="#3498db", fg="white", command=ouvrir_changer_compte)
        btn_changer.pack(pady=10, fill="x", padx=20)

        btn_mot_de_passe = tk.Button(
            frame_central,
            text="🔑 Changer mon mot de passe",
            font=("Arial", 10),
            bg="#8e44ad",
            fg="white",
            command=lambda: self.ouvrir_changement_mot_de_passe(self.compte_actif, fenetre),
        )
        btn_mot_de_passe.pack(pady=10, fill="x", padx=20)
        
        # === NOUVEAU : Bouton "Supprimer finance" ===
        def ouvrir_supprimer_finance():
            position = fenetre.geometry()
            fenetre.destroy()
            self.supprimer_finance(position)

        btn_supprimer = tk.Button(frame_central, text="🗑️ Supprimer finance", font=("Arial", 10), bg="#e67e22", fg="white", command=ouvrir_supprimer_finance)
        btn_supprimer.pack(pady=10, fill="x", padx=20)

        # Sélecteur de langue
        langue_frame = tk.Frame(frame_central, bg="#f0f0f0")
        langue_frame.pack(pady=10, fill="x", padx=20)
        tk.Label(langue_frame, text="🌐 Langue :", font=("Arial", 10), bg="#f0f0f0").pack(side="left")
        langue_combo = ttk.Combobox(langue_frame, values=["FR", "ARABE"], state="readonly", width=10)
        langue_combo.set(self.langue)
        langue_combo.pack(side="right")
        langue_combo.bind("<<ComboboxSelected>>", lambda e: self.changer_langue(langue_combo.get()))

        # Bouton "Déconnexion"
        def deconnecter():
            fenetre.destroy()
            self.compte_actif = None
            self.root.withdraw()
            self.selectionner_compte(initial=True)

        btn_deco = tk.Button(frame_central, text="🔒 Déconnexion", font=("Arial", 10), bg="#e74c3c", fg="white", command=deconnecter)
        btn_deco.pack(pady=20, fill="x", padx=20)

    def ouvrir_changement_mot_de_passe(self, compte, parent):
        """Change le mot de passe d'un compte après authentification avec l'ancien."""
        fenetre = tk.Toplevel(parent)
        fenetre.title("Changer le mot de passe")
        fenetre.geometry("360x300")
        fenetre.resizable(False, False)
        fenetre.transient(parent)
        fenetre.grab_set()
        fenetre.configure(bg="#f0f0f0")

        tk.Label(
            fenetre,
            text=f"Modifier le mot de passe de {compte}",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0",
        ).pack(pady=(16, 10))

        champs = []
        for etiquette in (
            "Mot de passe actuel :",
            "Nouveau mot de passe (8 caractères minimum) :",
            "Confirmer le nouveau mot de passe :",
        ):
            tk.Label(fenetre, text=etiquette, bg="#f0f0f0").pack(anchor="w", padx=24)
            champ = tk.Entry(fenetre, show="*", font=("Arial", 11))
            champ.pack(fill="x", padx=24, pady=(2, 8))
            champs.append(champ)

        ancien, nouveau, confirmation = champs

        def enregistrer():
            ancien_mdp = ancien.get()
            nouveau_mdp = nouveau.get()
            confirmation_mdp = confirmation.get()
            if not ancien_mdp:
                messagebox.showwarning("Champ requis", "Entrez votre mot de passe actuel.", parent=fenetre)
                ancien.focus_set()
                return
            if len(nouveau_mdp) < 8:
                messagebox.showwarning(
                    "Mot de passe invalide",
                    "Le nouveau mot de passe doit contenir au moins 8 caractères.",
                    parent=fenetre,
                )
                nouveau.focus_set()
                return
            if nouveau_mdp != confirmation_mdp:
                messagebox.showwarning(
                    "Confirmation incorrecte",
                    "Les deux nouveaux mots de passe ne correspondent pas.",
                    parent=fenetre,
                )
                confirmation.focus_set()
                return
            try:
                if not database.update_password(compte, ancien_mdp, nouveau_mdp):
                    messagebox.showerror(
                        "Échec",
                        "Le mot de passe actuel est incorrect.",
                        parent=fenetre,
                    )
                    ancien.delete(0, tk.END)
                    ancien.focus_set()
                    return
            except Exception as error:
                messagebox.showerror(
                    "Erreur",
                    f"Impossible de modifier le mot de passe :\n{error}",
                    parent=fenetre,
                )
                return
            messagebox.showinfo("Succès", "Votre mot de passe a été modifié.", parent=fenetre)
            fenetre.destroy()

        tk.Button(
            fenetre,
            text="Enregistrer le nouveau mot de passe",
            bg="#3498db",
            fg="white",
            command=enregistrer,
        ).pack(fill="x", padx=24, pady=(4, 12))
        ancien.focus_set()

    def changer_langue(self, langue):
        self.langue = langue
        messagebox.showinfo("Langue", f"Langue changée en {langue}")

    def ajouter_compte(self, fenetre_parent=None, position=None, on_success=None, on_cancel=None):
        """Ouvre une fenêtre pour ajouter un compte avec nom, email et mot de passe"""
        ajout_fenetre = tk.Toplevel(self.root)
        ajout_fenetre.title("Ajouter un compte")
        ajout_fenetre.geometry("300x300")
        ajout_fenetre.resizable(False, False)
        # La racine reste masquée pendant la création du premier compte.
        if self.root.state() != "withdrawn":
            ajout_fenetre.transient(self.root)
        ajout_fenetre.grab_set()
        ajout_fenetre.configure(bg="#f0f0f0")

        
        # === MODIFICATION ICI : Utiliser la position si fournie ===
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        param_width = 300
        param_height = 300
        if position:
            ajout_fenetre.geometry(position)
        else:
            # Même position que les paramètres par défaut
            self.root.update_idletasks()
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            x = main_x + (main_width - param_width)  # 20px de marge depuis la gauche
            y = main_y + 85  # 85px depuis le haut
            ajout_fenetre.geometry(f"300x300+{x}+{y}")

        frame_central = tk.Frame(ajout_fenetre, bg="#f0f0f0")
        frame_central.pack(expand=True, padx=20, pady=20)


        # Nom d'utilisateur
        tk.Label(frame_central, text="Nom d'utilisateur :", bg="#f0f0f0").pack(pady=5)
        entry_nom = tk.Entry(frame_central, font=("Arial", 12))
        entry_nom.pack(pady=5, padx=20, fill="x")

        # Email
        tk.Label(frame_central, text="Adresse email :", bg="#f0f0f0").pack(pady=5)
        entry_email = tk.Entry(frame_central, font=("Arial", 12))
        entry_email.pack(pady=5, padx=20, fill="x")

        # Mot de passe
        tk.Label(frame_central, text="Mot de passe :", bg="#f0f0f0").pack(pady=5)
        entry_mdp = tk.Entry(frame_central, font=("Arial", 12), show="*")
        entry_mdp.pack(pady=5, padx=20, fill="x")

        # Bouton Ajouter
        def ajouter():
            nom = entry_nom.get().strip()
            email = entry_email.get().strip()
            mdp = entry_mdp.get()

            if not nom:
                messagebox.showwarning("Erreur", "Nom d'utilisateur obligatoire.")
                return
            if not email or "@" not in email:
                messagebox.showwarning("Erreur", "Email invalide.")
                return
            if not mdp or len(mdp) < 8:
                messagebox.showwarning("Erreur", "Mot de passe trop court (minimum 8 caractères).")
                return

            if database.ajouter_compte(nom, email, mdp):
                messagebox.showinfo("Succès", f"Compte '{nom}' créé avec succès.")
                ajout_fenetre.destroy()
                if on_success:
                    on_success(nom)
            else:
                messagebox.showwarning("Erreur", "Ce nom ou email existe déjà.")

        btn_ajouter = tk.Button(frame_central, text="✅ Ajouter", bg="#2ecc71", fg="white", command=ajouter)
        btn_ajouter.pack(pady=10, padx=20, fill="x")
        
        # === MODIFICATION ICI : Ajouter un bouton Retour ===
        def retour_parametres():
            ajout_fenetre.destroy()
            self.ouvrir_fenetre_parametres()  # Rouvrir les paramètres

        btn_retour = tk.Button(
            frame_central, text="⬅ Retour", bg="#95a5a6", fg="white",
            command=(on_cancel if on_cancel else retour_parametres),
            state=("disabled" if on_cancel else "normal")
        )
        btn_retour.pack(pady=5, padx=20, fill="x")

        # Bouton Annuler
        def annuler_creation():
            ajout_fenetre.destroy()
            if on_cancel:
                on_cancel()

        btn_annuler = tk.Button(frame_central, text="❌ Annuler", bg="#e74c3c", fg="white", command=annuler_creation)
        btn_annuler.pack(pady=5, padx=20, fill="x")
        if on_cancel:
            ajout_fenetre.protocol("WM_DELETE_WINDOW", annuler_creation)

    def ouvrir_recuperation_mot_de_passe(self, compte, parent):
        """Guide l'utilisateur à travers les trois étapes de récupération du compte."""
        fenetre = tk.Toplevel(parent)
        fenetre.title("Récupération du mot de passe")
        fenetre.geometry("450x390")
        fenetre.resizable(False, False)
        fenetre.transient(parent)
        fenetre.grab_set()
        fenetre.configure(bg="#f0f0f0")
        tk.Label(fenetre, text=f"Récupération du compte {compte}", font=("Arial", 13, "bold"), bg="#f0f0f0").pack(pady=(14, 6))
        tk.Label(fenetre, text="Étape 1 — Vérifiez l'adresse e-mail du compte.", bg="#f0f0f0").pack(pady=5)

        form = tk.Frame(fenetre, bg="#f0f0f0")
        form.pack(fill="x", padx=24)
        tk.Label(form, text="Adresse e-mail du compte :", bg="#f0f0f0").pack(anchor="w")
        email_entry = tk.Entry(form, font=("Arial", 11))
        email_entry.pack(fill="x", pady=(1, 8))

        code_frame = tk.Frame(fenetre, bg="#f0f0f0")
        tk.Label(code_frame, text="Étape 2 — Saisissez le code reçu par e-mail :", bg="#f0f0f0").pack(anchor="w")
        code_entry = tk.Entry(code_frame, font=("Arial", 11))
        code_entry.pack(fill="x", pady=(1, 5))

        password_frame = tk.Frame(fenetre, bg="#f0f0f0")
        tk.Label(password_frame, text="Étape 3 — Choisissez un nouveau mot de passe (8 caractères minimum) :", bg="#f0f0f0", wraplength=390, justify="left").pack(anchor="w")
        nouveau_entry = tk.Entry(password_frame, font=("Arial", 11), show="*")
        nouveau_entry.pack(fill="x", pady=(1, 5))
        tk.Label(password_frame, text="Confirmez le nouveau mot de passe :", bg="#f0f0f0").pack(anchor="w")
        confirmation_entry = tk.Entry(password_frame, font=("Arial", 11), show="*")
        confirmation_entry.pack(fill="x", pady=(1, 5))
        etat = {"email": None, "code_verifie": False}

        def envoyer_code():
            email = email_entry.get().strip()
            adresse = database.get_account_email(compte)
            if not adresse or not email or not hmac.compare_digest(email.casefold(), adresse.strip().casefold()):
                messagebox.showerror("Vérification impossible", "Cette adresse ne correspond pas à celle du compte.", parent=fenetre)
                return
            database._recovery_codes.pop(compte, None)
            etat.update(email=None, code_verifie=False)
            code_frame.pack_forget()
            password_frame.pack_forget()
            host, user, password = (os.environ.get(k) for k in ("SGD_SMTP_HOST", "SGD_SMTP_USER", "SGD_SMTP_PASSWORD"))
            sender = os.environ.get("SGD_SMTP_FROM", user or "")
            try:
                port = int(os.environ.get("SGD_SMTP_PORT", "465"))
                if not all((host, user, password, sender)) or not 1 <= port <= 65535:
                    raise ValueError("SMTP non configuré ou port invalide")
                code = f"{secrets.randbelow(1_000_000):06d}"
                mail = EmailMessage()
                mail["Subject"], mail["From"], mail["To"] = "Code de récupération SGD", sender, adresse
                mail.set_content(f"Votre code de récupération SGD : {code}\n\nIl expire dans 10 minutes. Si vous n'avez pas demandé cette opération, ignorez ce message.")
                tls = ssl.create_default_context()
                if port == 465:
                    with smtplib.SMTP_SSL(host, port, context=tls, timeout=20) as smtp:
                        smtp.login(user, password)
                        smtp.send_message(mail)
                else:
                    with smtplib.SMTP(host, port, timeout=20) as smtp:
                        smtp.ehlo()
                        smtp.starttls(context=tls)
                        smtp.ehlo()
                        smtp.login(user, password)
                        smtp.send_message(mail)
            except (OSError, ValueError, smtplib.SMTPException) as erreur:
                messagebox.showerror("Échec de l'envoi", f"Vérifiez les paramètres SMTP.\n{erreur}", parent=fenetre)
                return
            if not database.create_recovery_code(compte, adresse, code):
                messagebox.showerror("Envoi annulé", "Le compte ou son adresse e-mail a changé. Recommencez la demande.", parent=fenetre)
                return
            etat["email"] = adresse
            code_frame.pack(fill="x", padx=24, pady=(12, 4))
            messagebox.showinfo("Code envoyé", "Un code a été envoyé à l'adresse du compte. Il expire dans 10 minutes.", parent=fenetre)
            code_entry.focus_set()

        def verifier_code():
            if not etat["email"]:
                messagebox.showwarning("Code requis", "Vérifiez d'abord votre adresse et demandez un code.", parent=fenetre)
                return
            if not database.verify_recovery_code(compte, etat["email"], code_entry.get().strip()):
                messagebox.showerror("Code invalide", "Le code est incorrect, expiré ou a dépassé le nombre d'essais. Demandez un nouveau code.", parent=fenetre)
                return
            etat["code_verifie"] = True
            code_frame.pack_forget()
            password_frame.pack(fill="x", padx=24, pady=(12, 4))
            messagebox.showinfo("Adresse vérifiée", "Code confirmé. Vous pouvez maintenant choisir un nouveau mot de passe.", parent=fenetre)
            nouveau_entry.focus_set()

        def reinitialiser():
            if not etat["code_verifie"]:
                messagebox.showwarning("Vérification requise", "Confirmez d'abord le code reçu par e-mail.", parent=fenetre)
                return
            nouveau = nouveau_entry.get()
            if len(nouveau) < 8 or nouveau != confirmation_entry.get():
                messagebox.showwarning("Mot de passe invalide", "Saisissez deux fois le même mot de passe (8 caractères minimum).", parent=fenetre)
                return
            try:
                resultat = database.reset_password(compte, etat["email"], nouveau)
            except (ValueError, PermissionError) as erreur:
                messagebox.showerror("Réinitialisation impossible", str(erreur), parent=fenetre)
                return
            if not resultat:
                etat["code_verifie"] = False
                code_frame.pack(fill="x", padx=24, pady=(12, 4))
                password_frame.pack_forget()
                messagebox.showerror("Réinitialisation impossible", "La vérification a expiré ou l'adresse du compte a changé. Demandez un nouveau code.", parent=fenetre)
                return
            messagebox.showinfo("Mot de passe modifié", "Vous pouvez maintenant vous connecter avec le nouveau mot de passe.", parent=fenetre)
            fenetre.destroy()

        tk.Button(fenetre, text="Vérifier l'adresse et envoyer le code", bg="#3498db", fg="white", command=envoyer_code).pack(fill="x", padx=24, pady=5)
        tk.Button(code_frame, text="Confirmer le code", bg="#2ecc71", fg="white", command=verifier_code).pack(fill="x", pady=5)
        tk.Button(password_frame, text="Enregistrer le nouveau mot de passe", bg="#2ecc71", fg="white", command=reinitialiser).pack(fill="x", pady=5)
        email_entry.focus_set()

    def selectionner_compte(self, fenetre_parent=None, position=None, initial=False):
        """Ouvre une fenêtre pour sélectionner un compte, puis demande le mot de passe"""
        select_fenetre = tk.Toplevel(self.root)
        select_fenetre.title("Changer de compte")
        select_fenetre.geometry("300x350")
        select_fenetre.resizable(False, False)
        # Ne pas rendre la fenêtre transitoire au premier lancement : la racine
        # est masquée jusqu'à l'authentification, et Windows masquerait alors
        # aussi cette fenêtre de connexion.
        if not initial:
            select_fenetre.transient(self.root)
        select_fenetre.grab_set()
        select_fenetre.configure(bg="#f0f0f0")

        # === MODIFICATION ICI : Utiliser la position si fournie ===
        if position:
            select_fenetre.geometry(position)
        else:
            # Position par défaut si aucune position n'est fournie
            select_fenetre.geometry("300x350")
            
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        param_width = 300
        param_height = 350
        if position:
            select_fenetre.geometry(position)
        else:
            # Même position que les paramètres par défaut
            self.root.update_idletasks()
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            x = main_x + (main_width - param_width)  # 20px de marge depuis la gauche
            y = main_y + 85  # 85px depuis le haut
            select_fenetre.geometry(f"300x350+{x}+{y}")

        tk.Label(select_fenetre, text="Sélectionnez un compte", font=("Arial", 14, "bold"), bg="#f0f0f0").pack(pady=10)

        def creer_nouveau_compte():
            position_creation = select_fenetre.geometry()
            select_fenetre.destroy()
            self.ajouter_compte(
                position=position_creation,
                on_success=(self._connexion_initiale if initial else None),
                on_cancel=(self.root.destroy if initial else None),
            )

        btn_creer_compte = tk.Button(
            select_fenetre,
            text="➕ Créer un nouveau compte",
            bg="#2ecc71",
            fg="white",
            command=creer_nouveau_compte,
        )
        btn_creer_compte.pack(pady=5, padx=20, fill="x")

        comptes = database.get_all_comptes()
        if not comptes:
            messagebox.showinfo("Info", "Aucun compte disponible.")
            select_fenetre.destroy()
            self.ajouter_compte(
                on_success=self._connexion_initiale,
                on_cancel=(self.root.destroy if initial else None),
            )
            return

        if initial:
            select_fenetre.protocol("WM_DELETE_WINDOW", self.root.destroy)

        listbox = tk.Listbox(select_fenetre, font=("Arial", 12), bg="white", relief="flat")
        for compte in comptes:
            listbox.insert(tk.END, compte)
        listbox.pack(pady=10, padx=20, fill="both", expand=True)

        def on_select(event=None):
            selection = listbox.curselection()
            if not selection:
                return
            compte_choisi = listbox.get(selection[0])
            select_fenetre.destroy()

            mdp_fenetre = tk.Toplevel(self.root)
            mdp_fenetre.title(f"Connexion - {compte_choisi}")
            mdp_fenetre.geometry("300x250")
            mdp_fenetre.resizable(False, False)
            # Lors de la connexion initiale, la racine est cachée; ne pas
            # rattacher la fenêtre modale à une fenêtre invisible.
            if not initial:
                mdp_fenetre.transient(self.root)
            mdp_fenetre.grab_set()
            mdp_fenetre.configure(bg="#f0f0f0")
            if initial:
                mdp_fenetre.protocol("WM_DELETE_WINDOW", self.root.destroy)
            else:
                mdp_fenetre.protocol("WM_DELETE_WINDOW", mdp_fenetre.destroy)
                
            # === MODIFICATION ICI : Utiliser la position si fournie ===
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            param_width = 300
            param_height = 300
            if position:
                # Garder la position du sélecteur sans reprendre sa hauteur (350 px).
                suffixe_position = position[position.find("+"):] if "+" in position else ""
                mdp_fenetre.geometry(f"300x250{suffixe_position}")
            else:
                # Même position que les paramètres par défaut
                self.root.update_idletasks()
                main_x = self.root.winfo_x()
                main_y = self.root.winfo_y()
                x = main_x + (main_width - param_width)  # 20px de marge depuis la gauche
                y = main_y + 85  # 85px depuis le haut
                mdp_fenetre.geometry(f"300x250+{x}+{y}")
                
            tk.Label(mdp_fenetre, text=f"Entrez le mot de passe pour {compte_choisi}", font=("Arial", 12), bg="#f0f0f0").pack(pady=10)

            entry_mdp = tk.Entry(mdp_fenetre, font=("Arial", 12), show="*")
            entry_mdp.pack(pady=10, padx=20, fill="x")

            def tenter_connexion():
                mdp = entry_mdp.get()
                if not mdp:
                    return
                if database.verifier_connexion(compte_choisi, mdp):
                    self.compte_actif = compte_choisi
                    messagebox.showinfo("Succès", f"Connecté en tant que {compte_choisi}.")
                    mdp_fenetre.destroy()
                    if fenetre_parent is not None:
                        fenetre_parent.destroy()
                    self.root.deiconify()
                    self.show_frame("accueil")
                else:
                    messagebox.showerror("Erreur", "Mot de passe incorrect.")

            btn_login = tk.Button(mdp_fenetre, text="Se connecter", bg="#3498db", fg="white", command=tenter_connexion)
            btn_login.pack(pady=10, padx=20, fill="x")

            def mot_de_passe_oublie():
                self.ouvrir_recuperation_mot_de_passe(compte_choisi, mdp_fenetre)

            btn_reset = tk.Button(
                mdp_fenetre,
                text="Mot de passe oublié ?",
                bg="#f39c12",
                fg="white",
                command=mot_de_passe_oublie,
            )
            btn_reset.pack(pady=5, padx=20, fill="x")
            # === MODIFICATION ICI : Ajouter un bouton Retour ===
            def retour_comptes():
                mdp_fenetre.destroy()
                self.selectionner_compte(initial=initial)  # Rouvrir les comptes
                
            btn_retour = tk.Button(mdp_fenetre, text="⬅ Retour", bg="#95a5a6", fg="white", command=retour_comptes)
            btn_retour.pack(pady=5, padx=20, fill="x")

        listbox.bind("<Double-1>", on_select)
        
        # === MODIFICATION ICI : Ajouter un bouton Retour ===
        def retour_parametres():
            select_fenetre.destroy()
            self.ouvrir_fenetre_parametres()  # Rouvrir les paramètres
            
        btn_retour = tk.Button(
            select_fenetre, text="⬅ Retour", bg="#95a5a6", fg="white",
            command=retour_parametres,
            state=("disabled" if initial else "normal"),
        )
        btn_retour.pack(pady=5, padx=20, fill="x")

        btn_annuler = tk.Button(
            select_fenetre, text="❌ Annuler", bg="#e74c3c", fg="white",
            command=(self.root.destroy if initial else select_fenetre.destroy)
        )
        btn_annuler.pack(pady=10, padx=20, fill="x")

    def supprimer_finance(self, position=None):
        """Ouvre une fenêtre pour supprimer les finances récentes"""
        supp_fenetre = tk.Toplevel(self.root)
        supp_fenetre.title("Supprimer des finances")
        supp_fenetre.geometry("800x500")
        supp_fenetre.resizable(False, False)
        supp_fenetre.transient(self.root)
        supp_fenetre.grab_set()
        supp_fenetre.configure(bg="#f0f0f0")
        
        # Positionner la fenêtre
        if position:
            # Extraire les dimensions de la position
            parts = position.split('+')
            if len(parts) >= 2:
                x = int(parts[1]) -500
                y = parts[2] if len(parts) > 2 else "85"
                supp_fenetre.geometry(f"800x500+{x}+{y}")
        else:
            self.root.update_idletasks()
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            x = main_x + (main_width - 800) // 2 
            y = main_y + 85
            supp_fenetre.geometry(f"800x500+{x}+{y}")
        
        # En-tête
        header_frame = tk.Frame(supp_fenetre, bg="#34495e", height=50)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame, 
            text="🗑️ Supprimer des finances", 
            font=("Arial", 14, "bold"), 
            bg="#34495e", 
            fg="white"
        ).pack(pady=10)
        
        # Frame pour la liste avec scrollbar
        list_frame = tk.Frame(supp_fenetre, bg="white")
        list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Canvas et scrollbar pour la liste défilante
        canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Récupérer les finances
        finances = database.get_dernieres_finances(self.compte_actif, limit=50)
        
        if not finances:
            tk.Label(
                scrollable_frame, 
                text="Aucune finance à afficher", 
                font=("Arial", 12), 
                bg="white", 
                fg="#7f8c8d"
            ).pack(pady=50)
        else:
            # En-têtes de colonnes
            header_row = tk.Frame(scrollable_frame, bg="#ecf0f1", height=40)
            header_row.pack(fill="x", pady=(0, 5))
            
            tk.Label(header_row, text="Type", font=("Arial", 10, "bold"), bg="#ecf0f1", width=10).pack(side="left", padx=5)
            tk.Label(header_row, text="Date", font=("Arial", 10, "bold"), bg="#ecf0f1", width=12).pack(side="left", padx=5)
            tk.Label(header_row, text="Catégorie", font=("Arial", 10, "bold"), bg="#ecf0f1", width=15).pack(side="left", padx=5)
            tk.Label(header_row, text="Montant", font=("Arial", 10, "bold"), bg="#ecf0f1", width=12).pack(side="left", padx=5)
            tk.Label(header_row, text="Description", font=("Arial", 10, "bold"), bg="#ecf0f1", width=20).pack(side="left", padx=5)
            tk.Label(header_row, text="Action", font=("Arial", 10, "bold"), bg="#ecf0f1", width=10).pack(side="left", padx=5)
            
            # Liste des finances
            for finance in finances:
                finance_id, date, montant, categorie, type_finance, description, fournisseur = finance
                
                # Frame pour chaque ligne
                row_frame = tk.Frame(scrollable_frame, bg="white", relief="solid", bd=1)
                row_frame.pack(fill="x", pady=2)
                
                # Couleur selon le type
                couleur_type = "#e74c3c" if type_finance == "Dépense" else "#2ecc71"
                
                # Type
                tk.Label(
                    row_frame, 
                    text=type_finance, 
                    font=("Arial", 9), 
                    bg=couleur_type, 
                    fg="white",
                    width=10
                ).pack(side="left", padx=5, pady=5)
                
                # Date
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    date_affichage = date_obj.strftime("%d/%m/%Y")
                except:
                    date_affichage = date
                
                tk.Label(row_frame, text=date_affichage, font=("Arial", 9), bg="white", width=12).pack(side="left", padx=(20,5))
                
                # Catégorie
                tk.Label(row_frame, text=categorie[:20], font=("Arial", 9), bg="white", width=15).pack(side="left", padx=(20,5))
                
                # Montant
                tk.Label(row_frame, text=f"{montant:.2f} TND", font=("Arial", 9, "bold"), bg="white", width=12).pack(side="left", padx=(20,5))
                
                # Description
                desc_text = description[:30] if description else "-"
                tk.Label(row_frame, text=desc_text, font=("Arial", 9), bg="white", width=20).pack(side="left", padx=(20,5))
                
                # Bouton Supprimer
                def supprimer_item(f_id=finance_id, f_type=type_finance, row=row_frame):
                    reponse = messagebox.askyesno(
                        "Confirmation",
                        f"Êtes-vous sûr de vouloir supprimer cette {f_type.lower()} ?\n\n"
                        f"Catégorie: {categorie}\n"
                        f"Montant: {montant:.2f} TND\n"
                        f"Date: {date_affichage}"
                    )
                    
                    if reponse:
                        if f_type == "Dépense":
                            success = database.delete_expense(f_id, self.compte_actif)
                        else:
                            success = database.delete_revenue(f_id, self.compte_actif)
                        
                        if success:
                            messagebox.showinfo("Succès", f"{f_type} supprimée avec succès.")
                            row.destroy()  # Supprimer visuellement la ligne
                            
                            # Mettre à jour les modules si nécessaire
                            if hasattr(self, 'accueil_module'):
                                self.accueil_module.afficher()
                            if hasattr(self, 'depenses_module') and f_type == "Dépense":
                                self.depenses_module.afficher()
                            if hasattr(self, 'revenus_module') and f_type == "Revenu":
                                self.revenus_module.afficher()
                        else:
                            messagebox.showerror("Erreur", "Échec de la suppression.")
                
                btn_supp = tk.Button(
                    row_frame, 
                    text="🗑️ Suppr.", 
                    font=("Arial", 8), 
                    bg="#e74c3c", 
                    fg="white",
                    command=supprimer_item,
                    width=10
                )
                btn_supp.pack(side="right", padx=5, pady=2)
        
        # Boutons de navigation en bas
        bottom_frame = tk.Frame(supp_fenetre, bg="#f0f0f0")
        bottom_frame.pack(fill="x", padx=20, pady=10)
        
        def retour_parametres():
            supp_fenetre.destroy()
            self.ouvrir_fenetre_parametres()
        
        btn_retour = tk.Button(
            bottom_frame, 
            text="⬅️ Retour", 
            bg="#95a5a6", 
            fg="white", 
            font=("Arial", 10),
            command=retour_parametres,
            width=15
        )
        btn_retour.pack(side="left", padx=5)
        
        btn_fermer = tk.Button(
            bottom_frame, 
            text="❌ Fermer", 
            bg="#34495e", 
            fg="white",
            font=("Arial", 10),
            command=supp_fenetre.destroy,
            width=15
        )
        btn_fermer.pack(side="right", padx=5)

    def mettre_a_jour_interface(self):
        """Met à jour l'affichage dans toutes les frames"""
        for frame_name, frame in self.frames.items():
            for widget in frame.winfo_children():
                widget.destroy()
            compte_label = tk.Label(frame, text=f"🏦 Compte actif : {self.compte_actif}", font=("Arial", 12, "bold"), bg="white", fg="#2c3e50")
            compte_label.pack(anchor="nw", padx=20, pady=10)
            label = tk.Label(frame, text=f"Contenu de l'onglet '{frame_name}' à venir...", font=("Arial", 16), bg="white")
            label.pack(expand=True)

    def show_frame(self, page_name):
        """Affiche la frame demandée"""
        frame = self.frames[page_name]
        frame.tkraise()

        titles = {
            "accueil": "SGD - Accueil",
            "revenus": "SGD - Revenus",
            "depenses": "SGD - Dépenses",
            "rapport": "SGD - Rapport"
        }
        self.root.title(titles[page_name])

        if page_name == "accueil":
            if not hasattr(self, 'accueil_module'):
                self.accueil_module = Accueil(frame, self.compte_actif)
            else:
                self.accueil_module.compte_actif = self.compte_actif
            self.accueil_module.afficher()
        
        elif page_name == "depenses":
            if not hasattr(self, 'depenses_module'):
                self.depenses_module = Depenses(frame, self.compte_actif)
            else:
                self.depenses_module.compte_actif = self.compte_actif
            self.depenses_module.afficher()
            
        elif page_name == "revenus":
            if not hasattr(self, 'revenus_module'):
                self.revenus_module = Revenus(frame, self.compte_actif)
            else:
                self.revenus_module.compte_actif = self.compte_actif
            self.revenus_module.afficher()
            
        elif page_name == "rapport":
            if not hasattr(self, 'rapport_module'):
                self.rapport_module = Rapport(frame, self.compte_actif)
            else:
                self.rapport_module.compte_actif = self.compte_actif
            self.rapport_module.afficher()
        
        elif not frame.winfo_children():
            self.mettre_a_jour_interface()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()